import pytest


def test_db_pool_env_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_POOL_SIZE", "7")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "3")
    monkeypatch.setenv("DB_POOL_TIMEOUT_S", "12")
    monkeypatch.setenv("DB_POOL_RECYCLE_S", "0")
    monkeypatch.setenv("DB_STATEMENT_TIMEOUT_MS", "0")

    import importlib

    import api.config

    config = importlib.reload(api.config)

    assert config.DB_POOL_SIZE == 7
    assert config.DB_MAX_OVERFLOW == 3
    assert config.DB_POOL_TIMEOUT_S == 12
    assert config.DB_POOL_RECYCLE_S == 0
    assert config.DB_STATEMENT_TIMEOUT_MS == 0


def test_db_pool_env_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_POOL_SIZE", "0")
    import importlib

    with pytest.raises(ValueError):
        import api.config

        importlib.reload(api.config)


def test_keycloak_env_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEYCLOAK_ISSUER_URL", "http://localhost:8080/realms/taste-kid")
    monkeypatch.setenv(
        "KEYCLOAK_JWKS_URL",
        "http://keycloak:8080/realms/taste-kid/protocol/openid-connect/certs",
    )
    monkeypatch.setenv("KEYCLOAK_AUDIENCE", "taste-kid-web")

    import importlib

    import api.config

    config = importlib.reload(api.config)

    assert config.KEYCLOAK_ISSUER_URL == "http://localhost:8080/realms/taste-kid"
    assert config.KEYCLOAK_JWKS_URL == "http://keycloak:8080/realms/taste-kid/protocol/openid-connect/certs"
    assert config.KEYCLOAK_AUDIENCE == "taste-kid-web"
