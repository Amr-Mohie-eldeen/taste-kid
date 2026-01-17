from pathlib import Path


def test_init_sql_defines_hnsw_cosine_index_for_movie_embeddings() -> None:
    init_sql_path = Path(__file__).parent / "../../../../infra/db/init.sql"
    sql = init_sql_path.read_text().lower()

    assert "using hnsw" in sql
    assert "vector_cosine_ops" in sql
