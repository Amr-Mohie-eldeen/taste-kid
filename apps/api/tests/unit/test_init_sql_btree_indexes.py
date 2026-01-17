from pathlib import Path


def test_init_sql_defines_vote_count_index() -> None:
    init_sql_path = Path(__file__).parent / "../../../../infra/db/init.sql"
    sql = init_sql_path.read_text().lower()

    assert "idx_movies_vote_count_desc" in sql


def test_init_sql_defines_user_ratings_updated_at_index() -> None:
    init_sql_path = Path(__file__).parent / "../../../../infra/db/init.sql"
    sql = init_sql_path.read_text().lower()

    assert "idx_user_movie_ratings_user_updated_desc" in sql
