import pytest
from httpx import AsyncClient
from sqlalchemy import text
import math

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post("/v1/users", json={"display_name": "Test User"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "id" in data
    assert data["display_name"] == "Test User"

@pytest.mark.asyncio
async def test_user_ratings_flow(client: AsyncClient, seeded_movies):
    # 1. Create User
    create_resp = await client.post("/v1/users", json={"display_name": "Rater"})
    user_id = create_resp.json()["data"]["id"]

    # 2. Rate a movie (Rating 5 -> Watched)
    movie_id = 1
    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": 5})
    assert response.status_code == 200

    # Verify status is watched
    response = await client.get(f"/v1/users/{user_id}/ratings")
    assert response.status_code == 200
    ratings = response.json()["data"]
    assert len(ratings) == 1
    assert ratings[0]["movie_id"] == movie_id if "movie_id" in ratings[0] else ratings[0]["id"] == movie_id
    assert ratings[0]["rating"] == 5
    assert ratings[0]["status"] == "watched"

    # 3. Update rating to None (-> Unwatched logic check)
    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": None, "status": "unwatched"})
    assert response.status_code == 200

    # Verify
    response = await client.get(f"/v1/users/{user_id}/ratings")
    ratings = response.json()["data"]
    assert len(ratings) == 1
    assert ratings[0]["status"] == "unwatched"
    assert ratings[0]["rating"] is None

@pytest.mark.asyncio
async def test_user_profile_stats(client: AsyncClient, seeded_movies):
    create_resp = await client.post("/v1/users", json={"display_name": "Stats User"})
    user_id = create_resp.json()["data"]["id"]

    # Rate movie 1 as 5 (Liked)
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"rating": 5})
    # Rate movie 2 as 3 (Neutral/Watched)
    await client.put(f"/v1/users/{user_id}/ratings/2", json={"rating": 3})

    response = await client.get(f"/v1/users/{user_id}/profile")
    assert response.status_code == 200
    stats = response.json()["data"]
    
    assert stats["user_id"] == user_id
    assert stats["num_ratings"] == 2 # 2 movies watched
    assert stats["num_liked"] == 1 # Only movie 1 is >= 4

@pytest.mark.asyncio
async def test_profile_embedding_weights(client: AsyncClient, seeded_movies, db_engine):
    """
    Verify that higher ratings shift the profile embedding closer to the movie 
    than lower (neutral) ratings.
    Movie 1: [0.1, ...]
    Movie 2: [0.2, ...]
    """
    create_resp = await client.post("/v1/users", json={"display_name": "Weighted User"})
    user_id = create_resp.json()["data"]["id"]

    # Rate Movie 1 (0.1) with 5 stars (Weight 1.0)
    # Rate Movie 2 (0.2) with 3 stars (Weight 0.2)
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"rating": 5})
    await client.put(f"/v1/users/{user_id}/ratings/2", json={"rating": 3})

    # Fetch profile embedding directly from DB
    with db_engine.begin() as conn:
        row = conn.execute(
            text("SELECT embedding FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id}
        ).fetchone()
    
    assert row is not None
    embedding = row[0]
    # Check first dimension. 
    # Weighted avg: (1.0 * 0.1 + 0.2 * 0.2) / 1.2 = (0.1 + 0.04) / 1.2 = 0.1166...
    # Midpoint would be 0.15. 
    # So it should be significantly closer to 0.1 than 0.2.
    val = embedding[0]
    assert val < 0.15
    assert abs(val - 0.116666) < 0.001

@pytest.mark.asyncio
async def test_dislike_isolation(client: AsyncClient, seeded_movies, db_engine):
    """
    Verify that low ratings (<=2) do NOT affect the positive profile embedding.
    """
    create_resp = await client.post("/v1/users", json={"display_name": "Dislike User"})
    user_id = create_resp.json()["data"]["id"]

    # Rate Movie 1 (0.1) with 5 stars (Liked)
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"rating": 5})
    
    # Rate Movie 2 (0.2) with 1 star (Disliked)
    await client.put(f"/v1/users/{user_id}/ratings/2", json={"rating": 1})

    # Fetch profile embedding
    with db_engine.begin() as conn:
        row = conn.execute(
            text("SELECT embedding FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id}
        ).fetchone()

    assert row is not None
    embedding = row[0]
    
    # The profile should ONLY reflect Movie 1.
    # Movie 2 should be completely ignored in the positive embedding.
    # So expected value is exactly 0.1
    assert abs(embedding[0] - 0.1) < 0.0001

@pytest.mark.asyncio
async def test_feed_source_switching(client: AsyncClient, seeded_movies):
    """
    Verify feed source switches from 'popularity' to 'profile' 
    once the user has a profile.
    """
    create_resp = await client.post("/v1/users", json={"display_name": "Feed User"})
    user_id = create_resp.json()["data"]["id"]

    # 1. Cold start: expect popularity
    resp = await client.get(f"/v1/users/{user_id}/feed")
    assert resp.status_code == 200
    feed = resp.json()["data"]
    # We might not get items if seeded_movies are few and logic filters them, 
    # but based on seeded_movies we have 3 items.
    assert len(feed) > 0
    assert feed[0]["source"] == "popularity"

    # 2. Rate a movie to create profile
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"rating": 5})

    # 3. Established user: expect profile
    resp = await client.get(f"/v1/users/{user_id}/feed")
    assert resp.status_code == 200
    feed = resp.json()["data"]
    assert len(feed) > 0
    # Note: Movie 1 is now rated, so it might be excluded depending on logic,
    # but we have Movie 2 and 3.
    assert feed[0]["source"] == "profile"

@pytest.mark.asyncio
async def test_state_transitions_and_deletion(client: AsyncClient, seeded_movies, db_engine):
    """
    Test that profile is created, updated, and deleted based on rating validity.
    """
    create_resp = await client.post("/v1/users", json={"display_name": "State User"})
    user_id = create_resp.json()["data"]["id"]

    def profile_exists():
        with db_engine.begin() as conn:
            return conn.execute(
                text("SELECT 1 FROM user_profiles WHERE user_id = :uid"),
                {"uid": user_id}
            ).fetchone() is not None

    # 1. Rate "unwatched" -> No profile
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"status": "unwatched", "rating": None})
    assert not profile_exists()

    # 2. Rate "watched", 5 stars -> Profile created
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"status": "watched", "rating": 5})
    assert profile_exists()

    # 3. Rate "watched", 2 stars (Dislike) -> Profile deleted (since it's the only rating)
    # Ratings <= 2 are ignored for positive profile calculation.
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"status": "watched", "rating": 2})
    assert not profile_exists()

    # 4. Rate "watched", 5 stars -> Profile recreated
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"status": "watched", "rating": 5})
    assert profile_exists()

    # 5. Delete rating (unwatched / None) -> Profile deleted
    await client.put(f"/v1/users/{user_id}/ratings/1", json={"status": "unwatched", "rating": None})
    assert not profile_exists()

@pytest.mark.asyncio
async def test_dislike_penalizes_recommendations(client: AsyncClient, db_engine):
    """
    Verify that disliking enough movies triggers the dislike penalization logic,
    pushing similar movies down in the recommendations.
    
    We need DISLIKE_MIN_COUNT (default 3) dislikes to trigger the logic.
    """
    create_resp = await client.post("/v1/users", json={"display_name": "Penalized User"})
    user_id = create_resp.json()["data"]["id"]

    # Geometric Setup (Normalized Vectors for consistent Cosine Distance):
    # Anchor: [1.0, 0.0, ...]
    # Candidate A: [0.707, 0.707, ...] (45 deg) -> Same distance to Anchor
    # Candidate B: [0.707, -0.707, ...] (-45 deg) -> Same distance to Anchor
    # Dislike Group: [0.0, -1.0, ...] (-90 deg) -> Much closer to B (-45) than A (+45)
    
    dim = 768
    def vec(vals):
        v = [0.0] * dim
        for i, val in enumerate(vals):
            v[i] = val
        return v

    movies = [
        {"id": 100, "title": "Anchor", "embedding": vec([1.0, 0.0])},
        {"id": 101, "title": "Candidate A", "embedding": vec([0.7071, 0.7071])},
        {"id": 102, "title": "Candidate B", "embedding": vec([0.7071, -0.7071])},
        # Dislikes clustered at -90 deg
        {"id": 201, "title": "Dislike 1", "embedding": vec([0.0, -1.0])},
        {"id": 202, "title": "Dislike 2", "embedding": vec([0.1, -0.9])}, # jittered slightly
        {"id": 203, "title": "Dislike 3", "embedding": vec([-0.1, -0.9])},
    ]

    with db_engine.begin() as conn:
        for m in movies:
            conn.execute(
                text("INSERT INTO movies (id, title, vote_average, vote_count, status, release_date, genres) VALUES (:id, :title, 5.0, 100, 'Released', '2020-01-01', 'Drama')"),
                {k: v for k, v in m.items() if k != "embedding"}
            )
            conn.execute(
                text("INSERT INTO movie_embeddings (movie_id, embedding, embedding_model, doc_hash) VALUES (:movie_id, :embedding, 'test', 'hash')"),
                {"movie_id": m["id"], "embedding": m["embedding"]}
            )

    # 1. Like the Anchor to build profile
    await client.put(f"/v1/users/{user_id}/ratings/100", json={"rating": 5})

    # 2. Get Recommendations (Baseline)
    resp = await client.get(f"/v1/users/{user_id}/recommendations")
    recs = resp.json()["data"]
    
    def get_score(mid, r_list):
        for x in r_list:
            if x["id"] == mid:
                return x.get("score") or x.get("similarity")
        return 0

    score_a_base = get_score(101, recs)
    score_b_base = get_score(102, recs)
    
    # Should be roughly equal (approx 0.29 distance each)
    assert abs(score_a_base - score_b_base) < 0.01

    # 3. Dislike the 3 "Dislike" movies
    for i in [201, 202, 203]:
        await client.put(f"/v1/users/{user_id}/ratings/{i}", json={"rating": 1})

    # 4. Get Recommendations (Penalized)
    resp = await client.get(f"/v1/users/{user_id}/recommendations")
    recs = resp.json()["data"]
    
    score_a_final = get_score(101, recs)
    score_b_final = get_score(102, recs)

    # Candidate B is closer to dislikes, so it should be penalized more.
    # Score = Similarity - (Weight * DislikeSimilarity)
    # A is far from dislike (orthogonal-ish), B is close.
    # So Score B should drop significantly compared to Score A.
    assert score_a_final > score_b_final + 0.1 # Expect significant gap
