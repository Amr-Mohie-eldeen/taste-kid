from pathlib import Path

import docker
import pytest
import pytest_asyncio
from docker.errors import DockerException
from httpx import ASGITransport, AsyncClient
from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, text
from testcontainers.postgres import PostgresContainer

import api.db
from api.main import app


def _docker_available() -> bool:
    client = None
    try:
        client = docker.from_env(timeout=5)
        client.ping()
        return True
    except DockerException:
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


@pytest.fixture(scope="session")
def postgres_container():
    if not _docker_available():
        pytest.skip("Docker daemon not reachable; start Docker to run integration tests")

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
    init_sql_path = Path(__file__).parent / "../../../infra/db/init.sql"
    with init_sql_path.open() as f:
        sql_script = f.read()

    # Remove the dynamic sizing block which causes issues in the test environment.
    # It's not needed since we start fresh with the schema-defined dimensions.
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
def embedding_dim(db_engine) -> int:
    q = text(
        """
        SELECT a.atttypmod - 4 AS dims
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'movie_embeddings'
          AND a.attname = 'embedding'
          AND n.nspname = 'public'
        """
    )
    with db_engine.begin() as conn:
        dims = conn.execute(q).scalar()
    assert isinstance(dims, int) and dims > 0
    return dims


@pytest.fixture(scope="session")
def seeded_movies(db_engine, embedding_dim):
    # Insert 3 movies with embeddings for similarity tests
    movies = [
        {
            "id": 1,
            "title": "Inception",
            "vote_average": 8.8,
            "vote_count": 10000,
            "status": "Released",
            "release_date": "2010-07-15",
            "runtime": 148,
            "original_language": "en",
            "genres": "Action,Science Fiction",
            "keywords": "dream,heist",
            "embedding": [0.1] * embedding_dim,
        },
        {
            "id": 2,
            "title": "The Matrix",
            "vote_average": 8.7,
            "vote_count": 9000,
            "status": "Released",
            "release_date": "1999-03-30",
            "runtime": 136,
            "original_language": "en",
            "genres": "Action,Science Fiction",
            "keywords": "simulation,ai",
            "embedding": [0.2] * embedding_dim,
        },
        {
            "id": 3,
            "title": "Interstellar",
            "vote_average": 8.6,
            "vote_count": 8000,
            "status": "Released",
            "release_date": "2014-11-05",
            "runtime": 169,
            "original_language": "en",
            "genres": "Adventure,Drama,Science Fiction",
            "keywords": "space,black hole",
            "embedding": [0.15] * embedding_dim,
        },
    ]
    with db_engine.begin() as conn:
        if conn.execute(text("SELECT COUNT(*) FROM movies")).scalar() == 0:
            for movie in movies:
                conn.execute(
                    text(
                        "INSERT INTO movies (id, title, vote_average, vote_count, status, release_date, runtime, original_language, genres, keywords) VALUES (:id, :title, :vote_average, :vote_count, :status, :release_date, :runtime, :original_language, :genres, :keywords)"
                    ),
                    {key: value for key, value in movie.items() if key != "embedding"},
                )
                conn.execute(
                    text(
                        "INSERT INTO movie_embeddings (movie_id, embedding, embedding_model, doc_hash) VALUES (:movie_id, :embedding, 'test', 'hash')"
                    ),
                    {"movie_id": movie["id"], "embedding": movie["embedding"]},
                )
    return {
        "inception_id": 1,
        "matrix_id": 2,
        "interstellar_id": 3,
        "embedding_dim": embedding_dim,
    }


@pytest_asyncio.fixture
async def client(db_session):  # noqa: ARG001
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
