from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from httpx import ASGITransport, AsyncClient

import api.v1.main as v1_main
from api.main import app


@dataclass
class _UserSummary:
    id: int
    display_name: str | None
    num_ratings: int
    profile_updated_at: str | None


def _stub_auth_db(monkeypatch: pytest.MonkeyPatch, user_id: int) -> None:
    def register_user(*, email: str, password_hash: str, display_name: str | None) -> int:  # noqa: ARG001
        return user_id

    def authenticate_user(*, email: str, password: str) -> int:  # noqa: ARG001
        return user_id

    def get_user_summary(_user_id: int) -> _UserSummary:
        return _UserSummary(
            id=user_id,
            display_name="Test",
            num_ratings=0,
            profile_updated_at=None,
        )

    monkeypatch.setattr(v1_main, "register_user", register_user)
    monkeypatch.setattr(v1_main, "authenticate_user", authenticate_user)
    monkeypatch.setattr(v1_main, "get_user_summary", get_user_summary)


@pytest.mark.asyncio
async def test_register_rate_limited(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RATE_LIMIT_REGISTER", "2/minute")
    _stub_auth_db(monkeypatch, user_id=101)

    transport = ASGITransport(app=app, client=("203.0.113.10", 123))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(2):
            resp = await client.post(
                "/v1/auth/register",
                json={
                    "email": f"test-{uuid.uuid4()}@example.com",
                    "password": "password123",
                    "display_name": "Test",
                },
            )
            assert resp.status_code == 200

        resp = await client.post(
            "/v1/auth/register",
            json={
                "email": f"test-{uuid.uuid4()}@example.com",
                "password": "password123",
                "display_name": "Test",
            },
        )
        assert resp.status_code == 429
        payload = resp.json()
        assert payload.get("error", {}).get("code") == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_login_rate_limited(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RATE_LIMIT_REGISTER", "1000/minute")
    monkeypatch.setenv("RATE_LIMIT_LOGIN", "2/minute")
    _stub_auth_db(monkeypatch, user_id=202)

    transport = ASGITransport(app=app, client=("203.0.113.11", 123))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"test-{uuid.uuid4()}@example.com"
        resp = await client.post(
            "/v1/auth/register",
            json={"email": email, "password": "password123", "display_name": "Test"},
        )
        assert resp.status_code == 200

        for _ in range(2):
            resp = await client.post(
                "/v1/auth/login",
                json={"email": email, "password": "password123"},
            )
            assert resp.status_code == 200

        resp = await client.post(
            "/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        assert resp.status_code == 429
        payload = resp.json()
        assert payload.get("error", {}).get("code") == "RATE_LIMITED"
