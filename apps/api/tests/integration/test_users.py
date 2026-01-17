from collections.abc import Sequence

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from api.config import DISLIKE_MIN_COUNT, DISLIKE_WEIGHT, NEUTRAL_RATING_WEIGHT


def _error_code(payload: dict) -> str:
    error = payload.get("error")
    assert isinstance(error, dict)
    code = error.get("code")
    assert isinstance(code, str)
    return code


def _fetch_vector(db_engine, sql: str, params: dict) -> list[float]:
    with db_engine.begin() as conn:
        row = conn.execute(text(sql), params).fetchone()

    assert row is not None, f"Expected row for query: {sql!r}"
    vector = row[0]
    assert vector is not None, "Expected vector column to be non-null"

    if hasattr(vector, "tolist"):
        values = vector.tolist()
    elif isinstance(vector, list):
        values = vector
    elif isinstance(vector, Sequence):
        values = list(vector)
    else:
        raise AssertionError(f"Unexpected vector type: {type(vector)!r}")

    assert values, "Expected vector to have at least one dimension"
    assert all(isinstance(value, (int, float)) for value in values)
    return [float(value) for value in values]


def _fetch_profile_embedding(db_engine, user_id: int) -> list[float]:
    return _fetch_vector(
        db_engine,
        "SELECT embedding FROM user_profiles WHERE user_id = :user_id",
        {"user_id": user_id},
    )


def _fetch_movie_embedding(db_engine, movie_id: int) -> list[float]:
    return _fetch_vector(
        db_engine,
        "SELECT embedding FROM movie_embeddings WHERE movie_id = :movie_id",
        {"movie_id": movie_id},
    )


def _profile_exists(db_engine, user_id: int) -> bool:
    with db_engine.begin() as conn:
        row = conn.execute(
            text("SELECT 1 FROM user_profiles WHERE user_id = :user_id"), {"user_id": user_id}
        ).fetchone()
    return row is not None


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post("/v1/users", json={"display_name": "Test User"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "id" in data
    assert data["display_name"] == "Test User"


@pytest.mark.asyncio
async def test_user_ratings_flow(client: AsyncClient, seeded_movies):  # noqa: ARG001
    # 1. Create User
    create_resp = await client.post("/v1/users", json={"display_name": "Rater"})
    user_id = create_resp.json()["data"]["id"]

    # 2. Rate a movie (Rating 5 -> Watched)
    movie_id = seeded_movies["inception_id"]
    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": 5})
    assert response.status_code == 200

    # Verify status is watched
    response = await client.get(f"/v1/users/{user_id}/ratings")
    assert response.status_code == 200
    ratings = response.json()["data"]
    assert len(ratings) == 1

    # Contract: ratings items use `id` (movie id).
    assert ratings[0]["id"] == movie_id
    assert ratings[0]["rating"] == 5
    assert ratings[0]["status"] == "watched"

    # 3. Update rating to None (-> Unwatched logic check)
    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": None, "status": "unwatched"}
    )
    assert response.status_code == 200

    # Verify
    response = await client.get(f"/v1/users/{user_id}/ratings")
    ratings = response.json()["data"]
    assert len(ratings) == 1
    assert ratings[0]["status"] == "unwatched"
    assert ratings[0]["rating"] is None


@pytest.mark.asyncio
async def test_rating_validation(client: AsyncClient, seeded_movies):
    create_resp = await client.post("/v1/users", json={"display_name": "Validator"})
    user_id = create_resp.json()["data"]["id"]
    movie_id = seeded_movies["inception_id"]

    # Invalid rating values should fail validation (pydantic)
    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": 6})
    assert response.status_code == 422
    assert _error_code(response.json()) == "VALIDATION_ERROR"

    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": -1})
    assert response.status_code == 422
    assert _error_code(response.json()) == "VALIDATION_ERROR"

    # Empty payload is accepted by schema, but rejected by business rules
    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={})
    assert response.status_code == 400
    assert _error_code(response.json()) == "BAD_REQUEST"

    # Invalid status should return a 400
    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        json={"status": "maybe"},
    )
    assert response.status_code == 400
    assert _error_code(response.json()) == "BAD_REQUEST"

    # Missing required fields for the simplified rate endpoint (movie_id required)
    response = await client.post(f"/v1/users/{user_id}/rate", json={})
    assert response.status_code == 422
    assert _error_code(response.json()) == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_nonexistent_resources(client: AsyncClient):
    response = await client.get("/v1/users/99999/profile")
    assert response.status_code == 404
    assert _error_code(response.json()) == "USER_NOT_FOUND"

    create_resp = await client.post("/v1/users", json={"display_name": "Missing Movie"})
    user_id = create_resp.json()["data"]["id"]

    response = await client.put(f"/v1/users/{user_id}/ratings/99999", json={"rating": 5})
    assert response.status_code == 404
    assert _error_code(response.json()) == "MOVIE_NOT_FOUND"


@pytest.mark.asyncio
async def test_rating_status_combinations(client: AsyncClient, seeded_movies, db_engine):
    create_resp = await client.post("/v1/users", json={"display_name": "Status Combo"})
    user_id = create_resp.json()["data"]["id"]
    movie_id = seeded_movies["inception_id"]

    # Edge case: watched + no rating is allowed, but should not create a profile
    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        json={"status": "watched", "rating": None},
    )
    assert response.status_code == 200

    response = await client.get(f"/v1/users/{user_id}/ratings")
    assert response.status_code == 200
    ratings = response.json()["data"]
    assert len(ratings) == 1
    assert ratings[0]["id"] == movie_id
    assert ratings[0]["status"] == "watched"
    assert ratings[0]["rating"] is None

    assert not _profile_exists(db_engine, user_id)


@pytest.mark.asyncio
async def test_neutral_rating_creates_profile(client: AsyncClient, seeded_movies, db_engine):
    create_resp = await client.post("/v1/users", json={"display_name": "Neutral"})
    user_id = create_resp.json()["data"]["id"]
    movie_id = seeded_movies["matrix_id"]

    await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": 3})

    assert _profile_exists(db_engine, user_id)

    response = await client.get(f"/v1/users/{user_id}/profile")
    assert response.status_code == 200
    stats = response.json()["data"]
    assert stats["num_ratings"] == 1
    assert stats["num_liked"] == 0

    profile_embedding = _fetch_profile_embedding(db_engine, user_id)
    movie_embedding = _fetch_movie_embedding(db_engine, movie_id)
    assert profile_embedding[0] == pytest.approx(movie_embedding[0], abs=1e-4)


@pytest.mark.asyncio
async def test_user_profile_stats(client: AsyncClient, seeded_movies):  # noqa: ARG001
    create_resp = await client.post("/v1/users", json={"display_name": "Stats User"})
    user_id = create_resp.json()["data"]["id"]

    # Rate movie 1 as 5 (Liked)
    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}", json={"rating": 5}
    )
    # Rate movie 2 as 3 (Neutral/Watched)
    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['matrix_id']}", json={"rating": 3}
    )

    response = await client.get(f"/v1/users/{user_id}/profile")
    assert response.status_code == 200
    stats = response.json()["data"]

    assert stats["user_id"] == user_id
    assert stats["num_ratings"] == 2  # 2 movies watched
    assert stats["num_liked"] == 1  # Only movie 1 is >= 4


@pytest.mark.asyncio
async def test_profile_embedding_weights(client: AsyncClient, seeded_movies, db_engine):  # noqa: ARG001
    """
    Verify that higher ratings shift the profile embedding closer to the movie
    than lower (neutral) ratings.
    Movie 1: [0.1, ...]
    Movie 2: [0.2, ...]
    """
    create_resp = await client.post("/v1/users", json={"display_name": "Weighted User"})
    user_id = create_resp.json()["data"]["id"]

    movie_1_id = seeded_movies["inception_id"]
    movie_2_id = seeded_movies["matrix_id"]

    # Rate Movie 1 with 5 stars (weight 1.0)
    # Rate Movie 2 with 3 stars (weight NEUTRAL_RATING_WEIGHT)
    await client.put(f"/v1/users/{user_id}/ratings/{movie_1_id}", json={"rating": 5})
    await client.put(f"/v1/users/{user_id}/ratings/{movie_2_id}", json={"rating": 3})

    profile_embedding = _fetch_profile_embedding(db_engine, user_id)
    movie_1_embedding = _fetch_movie_embedding(db_engine, movie_1_id)
    movie_2_embedding = _fetch_movie_embedding(db_engine, movie_2_id)

    # Validate we can safely index dimension 0
    assert len(profile_embedding) >= 1
    assert len(movie_1_embedding) >= 1
    assert len(movie_2_embedding) >= 1

    # Expected weighted average for dimension 0
    expected = (1.0 * movie_1_embedding[0] + NEUTRAL_RATING_WEIGHT * movie_2_embedding[0]) / (
        1.0 + NEUTRAL_RATING_WEIGHT
    )

    midpoint = (movie_1_embedding[0] + movie_2_embedding[0]) / 2.0
    assert profile_embedding[0] < midpoint
    assert profile_embedding[0] == pytest.approx(expected, abs=1e-3)


@pytest.mark.asyncio
async def test_dislike_isolation(client: AsyncClient, seeded_movies, db_engine):  # noqa: ARG001
    """
    Verify that low ratings (<=2) do NOT affect the positive profile embedding.
    """
    create_resp = await client.post("/v1/users", json={"display_name": "Dislike User"})
    user_id = create_resp.json()["data"]["id"]

    liked_movie_id = seeded_movies["inception_id"]
    disliked_movie_id = seeded_movies["matrix_id"]

    # Rate liked movie (watched)
    await client.put(f"/v1/users/{user_id}/ratings/{liked_movie_id}", json={"rating": 5})

    # Rate a disliked movie (<=2 ratings are excluded from the positive profile embedding)
    await client.put(f"/v1/users/{user_id}/ratings/{disliked_movie_id}", json={"rating": 1})

    profile_embedding = _fetch_profile_embedding(db_engine, user_id)
    liked_embedding = _fetch_movie_embedding(db_engine, liked_movie_id)

    assert profile_embedding[0] == pytest.approx(liked_embedding[0], abs=1e-4)


@pytest.mark.asyncio
async def test_feed_source_switching(client: AsyncClient, seeded_movies):  # noqa: ARG001
    """Verify feed source switches from 'popularity' to 'profile'."""
    create_resp = await client.post("/v1/users", json={"display_name": "Feed User"})
    user_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/v1/users/{user_id}/feed")
    assert resp.status_code == 200
    feed = resp.json()["data"]
    assert len(feed) > 0
    assert feed[0]["source"] == "popularity"

    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}",
        json={"rating": 5},
    )

    resp = await client.get(f"/v1/users/{user_id}/feed")
    assert resp.status_code == 200
    feed = resp.json()["data"]
    assert len(feed) > 0
    assert feed[0]["source"] == "profile"


@pytest.mark.asyncio
async def test_state_transitions_and_deletion(client: AsyncClient, seeded_movies, db_engine):  # noqa: ARG001
    """
    Test that profile is created, updated, and deleted based on rating validity.
    """
    create_resp = await client.post("/v1/users", json={"display_name": "State User"})
    user_id = create_resp.json()["data"]["id"]

    def profile_exists() -> bool:
        return _profile_exists(db_engine, user_id)

    movie_id = seeded_movies["inception_id"]

    # 1. Rate "unwatched" -> No profile
    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        json={"status": "unwatched", "rating": None},
    )
    assert not profile_exists()

    # 2. Rate "watched", 5 stars -> Profile created
    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        json={"status": "watched", "rating": 5},
    )
    assert profile_exists()

    # 3. Rate "watched", 2 stars (Dislike) -> Profile deleted (since it's the only rating)
    # Ratings <= 2 are ignored for positive profile calculation.
    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        json={"status": "watched", "rating": 2},
    )
    assert not profile_exists()

    # 4. Rate "watched", 5 stars -> Profile recreated
    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        json={"status": "watched", "rating": 5},
    )
    assert profile_exists()

    # 5. Delete rating (unwatched / None) -> Profile deleted
    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        json={"status": "unwatched", "rating": None},
    )
    assert not profile_exists()


@pytest.mark.asyncio
async def test_dislike_penalizes_recommendations(client: AsyncClient, db_engine, embedding_dim):
    """Verify the dislike vector penalizes recs after threshold.

    This test also covers threshold behavior:
    - With `DISLIKE_MIN_COUNT - 1` dislikes: no dislike penalty applied.
    - With `DISLIKE_MIN_COUNT` dislikes: penalty applied.

    Geometry (normalized vectors => stable cosine distance):
    - Anchor: [1, 0]
    - Candidate A: [+45°] => [1/sqrt(2), 1/sqrt(2)]
    - Candidate B: [-45°] => [1/sqrt(2), -1/sqrt(2)]
    - Dislikes: around [-90°] => [0, -1] (closer to B than A)
    """

    import math

    create_resp = await client.post("/v1/users", json={"display_name": "Penalized User"})
    user_id = create_resp.json()["data"]["id"]

    def vec(x0: float, x1: float) -> list[float]:
        values = [0.0] * embedding_dim
        values[0] = x0
        values[1] = x1
        return values

    inv_sqrt2 = 1.0 / math.sqrt(2.0)

    anchor_id = 100
    candidate_a_id = 101
    candidate_b_id = 102

    dislike_ids = [200 + idx for idx in range(DISLIKE_MIN_COUNT)]

    movies = [
        {"id": anchor_id, "title": "Anchor", "embedding": vec(1.0, 0.0)},
        {"id": candidate_a_id, "title": "Candidate A", "embedding": vec(inv_sqrt2, inv_sqrt2)},
        {"id": candidate_b_id, "title": "Candidate B", "embedding": vec(inv_sqrt2, -inv_sqrt2)},
    ]

    for idx, dislike_id in enumerate(dislike_ids):
        jitter = (idx - (DISLIKE_MIN_COUNT - 1) / 2.0) * 0.01
        movies.append(
            {"id": dislike_id, "title": f"Dislike {idx + 1}", "embedding": vec(jitter, -1.0)}
        )

    with db_engine.begin() as conn:
        for movie in movies:
            conn.execute(
                text(
                    "INSERT INTO movies (id, title, vote_average, vote_count, status, release_date, genres, runtime, original_language, keywords) "
                    "VALUES (:id, :title, 5.0, 100, 'Released', '2020-01-01', 'Drama', 120, 'en', '')"
                ),
                {key: value for key, value in movie.items() if key != "embedding"},
            )
            conn.execute(
                text(
                    "INSERT INTO movie_embeddings (movie_id, embedding, embedding_model, doc_hash) "
                    "VALUES (:movie_id, :embedding, 'test', 'hash')"
                ),
                {"movie_id": movie["id"], "embedding": movie["embedding"]},
            )

    await client.put(f"/v1/users/{user_id}/ratings/{anchor_id}", json={"rating": 5})

    def get_score(movie_id: int, recs: list[dict]) -> float:
        for item in recs:
            if item["id"] == movie_id:
                score = item.get("score")
                assert score is not None
                return float(score)
        raise AssertionError(f"movie_id {movie_id} not found in recommendations")

    # Baseline: A and B are symmetric around anchor => same score
    resp = await client.get(f"/v1/users/{user_id}/recommendations")
    assert resp.status_code == 200
    recs = resp.json()["data"]
    score_a_base = get_score(candidate_a_id, recs)
    score_b_base = get_score(candidate_b_id, recs)
    assert score_a_base == pytest.approx(score_b_base, abs=1e-3)

    # Below threshold: still no penalty applied
    for dislike_id in dislike_ids[: max(DISLIKE_MIN_COUNT - 1, 0)]:
        await client.put(f"/v1/users/{user_id}/ratings/{dislike_id}", json={"rating": 1})

    resp = await client.get(f"/v1/users/{user_id}/recommendations")
    assert resp.status_code == 200
    recs = resp.json()["data"]
    score_a_mid = get_score(candidate_a_id, recs)
    score_b_mid = get_score(candidate_b_id, recs)
    assert score_a_mid == pytest.approx(score_b_mid, abs=1e-3)

    # Reach threshold: penalty should kick in
    if DISLIKE_MIN_COUNT > 0:
        await client.put(f"/v1/users/{user_id}/ratings/{dislike_ids[-1]}", json={"rating": 1})

    resp = await client.get(f"/v1/users/{user_id}/recommendations")
    assert resp.status_code == 200
    recs = resp.json()["data"]
    score_a_final = get_score(candidate_a_id, recs)
    score_b_final = get_score(candidate_b_id, recs)

    # Candidate B is closer to dislikes, so it should be penalized more.
    min_expected_gap = max(0.01, DISLIKE_WEIGHT * 0.05)
    assert score_a_final > score_b_final + min_expected_gap
