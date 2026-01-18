import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, text
from testcontainers.postgres import PostgresContainer

import api.db
from api.main import app


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False

    try:
        subprocess.check_output(["docker", "info"], stderr=subprocess.STDOUT, text=True)
    except Exception:
        return False

    return True


def _ensure_docker_host_env() -> None:
    if os.environ.get("DOCKER_HOST"):
        return

    try:
        host = subprocess.check_output(
            ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
            text=True,
        ).strip()
    except Exception:
        return

    if host:
        os.environ["DOCKER_HOST"] = host


@pytest.fixture(scope="session")
def postgres_container():
    _ensure_docker_host_env()
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

    if not _docker_available():
        pytest.skip("Docker is required for integration tests")

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
    with db_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE user_movie_ratings, user_profiles, users CASCADE"))
    yield db_engine


@pytest.fixture(scope="session")
def embedding_dim(db_engine) -> int:
    q = text(
        """
        SELECT substring(format_type(a.atttypid, a.atttypmod) from '\\((\\d+)\\)')::int AS dims
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
    def _basis_embedding(index: int) -> list[float]:
        values = [0.0] * embedding_dim
        values[index % embedding_dim] = 1.0
        return values

    movies = [
        *[
            {
                "id": 1000 + i,
                "title": f"Movie {i}",
                "vote_average": 7.0,
                "vote_count": 1000 + i,
                "status": "Released",
                "release_date": "2000-01-01",
                "runtime": 100,
                "original_language": "en",
                "genres": "Action",
                "keywords": "test",
                "embedding": _basis_embedding(i),
            }
            for i in range(1, 101)
        ],
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


@pytest_asyncio.fixture
async def authed_user(client: AsyncClient) -> tuple[int, dict[str, str]]:
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Test"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    user_id = int(data["user"]["id"])
    token = data["access_token"]
    return user_id, {"Authorization": f"Bearer {token}"}
