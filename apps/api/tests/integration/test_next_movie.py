import pytest
from httpx import AsyncClient


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str, display_name: str) -> tuple[int, dict[str, str]]:
    resp = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": display_name},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    return int(data["user"]["id"]), _auth_headers(data["access_token"])


@pytest.mark.asyncio
async def test_next_movie_falls_back_to_popularity_when_no_profile(client: AsyncClient):
    user_id, headers = await _register(client, "next-user@example.com", "Next User")

    resp = await client.get(f"/v1/users/{user_id}/next", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "popularity"


@pytest.mark.asyncio
async def test_next_movie_uses_profile_when_profile_exists(client: AsyncClient, seeded_movies):  # noqa: ARG001
    user_id, headers = await _register(client, "next-profile@example.com", "Next Profile User")

    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}",
        headers=headers,
        json={"rating": 5},
    )

    resp = await client.get(f"/v1/users/{user_id}/next", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "profile"
