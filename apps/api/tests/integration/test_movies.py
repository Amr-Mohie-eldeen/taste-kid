import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_movie_detail(client: AsyncClient, seeded_movies):
    response = await client.get("/v1/movies/1")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == 1
    assert data["title"] == "Inception"
    assert "poster_url" in data

@pytest.mark.asyncio
async def test_lookup_movie(client: AsyncClient, seeded_movies):
    response = await client.get("/v1/movies/lookup?title=Inception")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == 1
    assert data["title"] == "Inception"

    response = await client.get("/v1/movies/lookup?title=NonExistent")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_similar_movies(client: AsyncClient, seeded_movies):
    # This verifies pgvector works as seeded_movies inserts embeddings
    response = await client.get("/v1/movies/1/similar")
    assert response.status_code == 200
    data = response.json()["data"]
    
    # We seeded 3 movies. Movie 1 is the anchor. 
    # Movies 2 and 3 should be returned as similar.
    ids = [m["id"] for m in data]
    assert 2 in ids
    assert 3 in ids
    assert 1 not in ids # Should not return itself usually, but check implementation if it filters itself.
    # api.similarity.get_similar_candidates does filter anchor: "WHERE m.id != :movie_id"
