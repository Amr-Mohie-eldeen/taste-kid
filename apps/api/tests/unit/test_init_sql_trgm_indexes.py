from pathlib import Path


def test_init_sql_enables_pg_trgm_extension() -> None:
    init_sql_path = Path(__file__).parent / "../../../../infra/db/init.sql"
    sql = init_sql_path.read_text().lower()

    assert "create extension if not exists pg_trgm" in sql


def test_init_sql_defines_trigram_indexes_for_titles() -> None:
    init_sql_path = Path(__file__).parent / "../../../../infra/db/init.sql"
    sql = init_sql_path.read_text().lower()

    assert "gin_trgm_ops" in sql
    assert "idx_movies_title_trgm" in sql
    assert "idx_movies_original_title_trgm" in sql
