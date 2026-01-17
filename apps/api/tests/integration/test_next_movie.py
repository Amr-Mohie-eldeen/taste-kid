import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_next_movie_falls_back_to_popularity_when_no_profile(client: AsyncClient):
    create_resp = await client.post("/v1/users", json={"display_name": "Next User"})
    user_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/v1/users/{user_id}/next")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "popularity"


@pytest.mark.asyncio
async def test_next_movie_uses_profile_when_profile_exists(client: AsyncClient, seeded_movies):  # noqa: ARG001
    create_resp = await client.post("/v1/users", json={"display_name": "Next Profile User"})
    user_id = create_resp.json()["data"]["id"]

    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}",
        json={"rating": 5},
    )

    resp = await client.get(f"/v1/users/{user_id}/next")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "profile"
