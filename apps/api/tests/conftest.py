import os
import time
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text, event
from testcontainers.postgres import PostgresContainer
from pgvector.psycopg import register_vector
import api.db
from api.main import app

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("pgvector/pgvector:pg16", driver="psycopg") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def db_engine(postgres_container):
    url = postgres_container.get_connection_url()
    engine = create_engine(url)
    
    # Resolve path to infra/db/init.sql relative to this file
    # tests/conftest.py -> .../apps/api/tests/conftest.py
    # repo root is 3 levels up from apps/api
    # actually, from apps/api/tests, it is ../../../infra/db/init.sql
    init_sql_path = os.path.join(
        os.path.dirname(__file__), 
        "../../../infra/db/init.sql"
    )
    with open(init_sql_path, "r") as f:
        sql_script = f.read()
    
    # Remove the dynamic sizing block which causes issues in test environment
    # and isn't needed since we start fresh with correct dimensions (768)
    if "DO $$" in sql_script:
        sql_script = sql_script.split("DO $$")[0]
    
    with engine.begin() as conn:
        conn.execute(text(sql_script))

    # Dispose of the pool so that subsequent connections (which will have the listener)
    # are fresh and trigger the _on_connect event.
    engine.dispose()

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _):
        register_vector(dbapi_conn)
            
    api.db._ENGINE = engine
    yield engine
    engine.dispose()
    api.db._ENGINE = None

@pytest.fixture(scope="function")
def db_session(db_engine):
    # Truncate tables to ensure clean state for each test
    with db_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE user_movie_ratings, users CASCADE"))
    yield db_engine

@pytest.fixture(scope="session")
def seeded_movies(db_engine):
    # Insert 3 movies with embeddings for similarity tests
    movies = [
        {"id": 1, "title": "Inception", "vote_average": 8.8, "vote_count": 10000, "status": "Released", "release_date": "2010-07-15", "runtime": 148, "original_language": "en", "genres": "Action,Science Fiction", "keywords": "dream,heist", "embedding": [0.1] * 768},
        {"id": 2, "title": "The Matrix", "vote_average": 8.7, "vote_count": 9000, "status": "Released", "release_date": "1999-03-30", "runtime": 136, "original_language": "en", "genres": "Action,Science Fiction", "keywords": "simulation,ai", "embedding": [0.2] * 768},
        {"id": 3, "title": "Interstellar", "vote_average": 8.6, "vote_count": 8000, "status": "Released", "release_date": "2014-11-05", "runtime": 169, "original_language": "en", "genres": "Adventure,Drama,Science Fiction", "keywords": "space,black hole", "embedding": [0.15] * 768}
    ]
    with db_engine.begin() as conn:
        if conn.execute(text("SELECT COUNT(*) FROM movies")).scalar() == 0:
            for m in movies:
                conn.execute(
                    text("INSERT INTO movies (id, title, vote_average, vote_count, status, release_date, runtime, original_language, genres, keywords) VALUES (:id, :title, :vote_average, :vote_count, :status, :release_date, :runtime, :original_language, :genres, :keywords)"),
                    {k: v for k, v in m.items() if k != "embedding"}
                )
                conn.execute(
                    text("INSERT INTO movie_embeddings (movie_id, embedding, embedding_model, doc_hash) VALUES (:movie_id, :embedding, 'test', 'hash')"),
                    {"movie_id": m["id"], "embedding": m["embedding"]}
                )

@pytest_asyncio.fixture
async def client(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
