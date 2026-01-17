from pathlib import Path


def test_init_sql_has_no_destructive_user_profiles_truncate() -> None:
    init_sql_path = Path(__file__).parent / "../../../../infra/db/init.sql"
    sql = init_sql_path.read_text()
    assert "TRUNCATE TABLE user_profiles" not in sql
