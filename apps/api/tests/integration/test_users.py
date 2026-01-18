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
async def test_user_ratings_flow(client: AsyncClient, seeded_movies, authed_user):  # noqa: ARG001
    user_id, headers = authed_user

    movie_id = seeded_movies["inception_id"]
    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"rating": 5},
    )
    assert response.status_code == 200

    response = await client.get(f"/v1/users/{user_id}/ratings", headers=headers)
    assert response.status_code == 200
    ratings = response.json()["data"]
    assert len(ratings) == 1

    assert ratings[0]["id"] == movie_id
    assert ratings[0]["rating"] == 5
    assert ratings[0]["status"] == "watched"

    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"rating": None, "status": "unwatched"},
    )
    assert response.status_code == 200

    response = await client.get(f"/v1/users/{user_id}/ratings", headers=headers)
    ratings = response.json()["data"]
    assert len(ratings) == 1
    assert ratings[0]["status"] == "unwatched"
    assert ratings[0]["rating"] is None


@pytest.mark.asyncio
async def test_rating_validation(client: AsyncClient, seeded_movies, authed_user):
    user_id, headers = authed_user
    movie_id = seeded_movies["inception_id"]

    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}", headers=headers, json={"rating": 6}
    )
    assert response.status_code == 422
    assert _error_code(response.json()) == "VALIDATION_ERROR"

    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}", headers=headers, json={"rating": -1}
    )
    assert response.status_code == 422
    assert _error_code(response.json()) == "VALIDATION_ERROR"

    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", headers=headers, json={})
    assert response.status_code == 400
    assert _error_code(response.json()) == "BAD_REQUEST"

    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"status": "maybe"},
    )
    assert response.status_code == 400
    assert _error_code(response.json()) == "BAD_REQUEST"

    response = await client.post(f"/v1/users/{user_id}/rate", headers=headers, json={})
    assert response.status_code == 422
    assert _error_code(response.json()) == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_nonexistent_movie_returns_404(client: AsyncClient, authed_user):
    user_id, headers = authed_user

    response = await client.put(
        f"/v1/users/{user_id}/ratings/99999", headers=headers, json={"rating": 5}
    )
    assert response.status_code == 404
    assert _error_code(response.json()) == "MOVIE_NOT_FOUND"


@pytest.mark.asyncio
async def test_user_endpoints_require_auth(client: AsyncClient, seeded_movies, authed_user):  # noqa: ARG001
    user_id, _headers = authed_user
    movie_id = seeded_movies["inception_id"]

    response = await client.get(f"/v1/users/{user_id}/profile")
    assert response.status_code == 401

    response = await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", json={"rating": 5})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cannot_access_other_users(client: AsyncClient, authed_user):
    _user_id, headers = authed_user

    register_resp = await client.post(
        "/v1/auth/register",
        json={
            "email": "other-user@example.com",
            "password": "password123",
            "display_name": "Other",
        },
    )
    other_user_id = register_resp.json()["data"]["user"]["id"]

    response = await client.get(f"/v1/users/{other_user_id}/profile", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rating_status_combinations(
    client: AsyncClient, seeded_movies, db_engine, authed_user
):
    user_id, headers = authed_user
    movie_id = seeded_movies["inception_id"]

    response = await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"status": "watched", "rating": None},
    )
    assert response.status_code == 200

    response = await client.get(f"/v1/users/{user_id}/ratings", headers=headers)
    assert response.status_code == 200
    ratings = response.json()["data"]
    assert len(ratings) == 1
    assert ratings[0]["id"] == movie_id
    assert ratings[0]["status"] == "watched"
    assert ratings[0]["rating"] is None

    assert not _profile_exists(db_engine, user_id)


@pytest.mark.asyncio
async def test_neutral_rating_creates_profile(
    client: AsyncClient, seeded_movies, db_engine, authed_user
):
    user_id, headers = authed_user
    movie_id = seeded_movies["matrix_id"]

    await client.put(f"/v1/users/{user_id}/ratings/{movie_id}", headers=headers, json={"rating": 3})

    assert _profile_exists(db_engine, user_id)

    response = await client.get(f"/v1/users/{user_id}/profile", headers=headers)
    assert response.status_code == 200
    stats = response.json()["data"]
    assert stats["num_ratings"] == 1
    assert stats["num_liked"] == 0

    profile_embedding = _fetch_profile_embedding(db_engine, user_id)
    movie_embedding = _fetch_movie_embedding(db_engine, movie_id)
    assert profile_embedding[0] == pytest.approx(movie_embedding[0], abs=1e-4)


@pytest.mark.asyncio
async def test_user_profile_stats(client: AsyncClient, seeded_movies, authed_user):  # noqa: ARG001
    user_id, headers = authed_user

    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}",
        headers=headers,
        json={"rating": 5},
    )
    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['matrix_id']}",
        headers=headers,
        json={"rating": 3},
    )

    response = await client.get(f"/v1/users/{user_id}/profile", headers=headers)
    assert response.status_code == 200
    stats = response.json()["data"]

    assert stats["user_id"] == user_id
    assert stats["num_ratings"] == 2
    assert stats["num_liked"] == 1


@pytest.mark.asyncio
async def test_profile_embedding_weights(
    client: AsyncClient, seeded_movies, db_engine, authed_user
):  # noqa: ARG001
    """
    Verify that higher ratings shift the profile embedding closer to the movie
    than lower (neutral) ratings.
    Movie 1: [0.1, ...]
    Movie 2: [0.2, ...]
    """
    user_id, headers = authed_user

    movie_1_id = seeded_movies["inception_id"]
    movie_2_id = seeded_movies["matrix_id"]

    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_1_id}", headers=headers, json={"rating": 5}
    )
    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_2_id}", headers=headers, json={"rating": 3}
    )

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
async def test_dislike_isolation(client: AsyncClient, seeded_movies, db_engine, authed_user):  # noqa: ARG001
    """
    Verify that low ratings (<=2) do NOT affect the positive profile embedding.
    """
    user_id, headers = authed_user

    liked_movie_id = seeded_movies["inception_id"]
    disliked_movie_id = seeded_movies["matrix_id"]

    await client.put(
        f"/v1/users/{user_id}/ratings/{liked_movie_id}", headers=headers, json={"rating": 5}
    )

    await client.put(
        f"/v1/users/{user_id}/ratings/{disliked_movie_id}", headers=headers, json={"rating": 1}
    )

    profile_embedding = _fetch_profile_embedding(db_engine, user_id)
    liked_embedding = _fetch_movie_embedding(db_engine, liked_movie_id)

    assert profile_embedding[0] == pytest.approx(liked_embedding[0], abs=1e-4)


@pytest.mark.asyncio
async def test_feed_source_switching(client: AsyncClient, seeded_movies, authed_user):  # noqa: ARG001
    """Verify feed source switches from 'popularity' to 'profile'."""
    user_id, headers = authed_user

    resp = await client.get(f"/v1/users/{user_id}/feed", headers=headers)
    assert resp.status_code == 200
    feed = resp.json()["data"]
    assert len(feed) > 0
    assert feed[0]["source"] == "popularity"

    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}",
        headers=headers,
        json={"rating": 5},
    )

    resp = await client.get(f"/v1/users/{user_id}/feed", headers=headers)
    assert resp.status_code == 200
    feed = resp.json()["data"]
    assert len(feed) > 0
    assert feed[0]["source"] == "profile"


@pytest.mark.asyncio
async def test_personalized_feed_pagination_has_no_duplicates(
    client: AsyncClient, seeded_movies, authed_user
):  # noqa: ARG001
    user_id, headers = authed_user

    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}",
        headers=headers,
        json={"rating": 5},
    )

    page_size = 20
    resp1 = await client.get(
        f"/v1/users/{user_id}/feed?k={page_size}&cursor=0",
        headers=headers,
    )
    assert resp1.status_code == 200
    payload1 = resp1.json()
    ids1 = [item["id"] for item in payload1["data"]]
    assert len(ids1) == page_size

    resp2 = await client.get(
        f"/v1/users/{user_id}/feed?k={page_size}&cursor={page_size}",
        headers=headers,
    )
    assert resp2.status_code == 200
    payload2 = resp2.json()
    ids2 = [item["id"] for item in payload2["data"]]
    assert len(ids2) == page_size

    assert len(set(ids1) & set(ids2)) == 0


@pytest.mark.asyncio
async def test_personalized_feed_does_not_span_windows(
    client: AsyncClient, seeded_movies, authed_user, monkeypatch
):  # noqa: ARG001
    monkeypatch.setattr("api.users.recommendations.MAX_FETCH_CANDIDATES", 50)
    monkeypatch.setattr(
        "api.users.recommendations.RECOMMENDATIONS_CACHE_MAX_WINDOWS_PER_REQUEST", 1
    )

    user_id, headers = authed_user

    await client.put(
        f"/v1/users/{user_id}/ratings/{seeded_movies['inception_id']}",
        headers=headers,
        json={"rating": 5},
    )

    page_size = 20
    # cursor=40 is near the end of window 0 when window_size=50.
    resp = await client.get(
        f"/v1/users/{user_id}/feed?k={page_size}&cursor=40",
        headers=headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    items = payload["data"]
    meta = payload["meta"]

    # We should only return the remaining items in the current window (50 - 40 = 10), not 20.
    assert len(items) == 10
    assert meta["has_more"] is True
    assert meta["next_cursor"] == "50"

    # Next page starts at the next window boundary.
    resp2 = await client.get(
        f"/v1/users/{user_id}/feed?k={page_size}&cursor=50",
        headers=headers,
    )
    assert resp2.status_code == 200
    payload2 = resp2.json()
    items2 = payload2["data"]

    assert len({item["id"] for item in items} & {item["id"] for item in items2}) == 0


@pytest.mark.asyncio
async def test_state_transitions_and_deletion(
    client: AsyncClient, seeded_movies, db_engine, authed_user
):  # noqa: ARG001
    """
    Test that profile is created, updated, and deleted based on rating validity.
    """
    user_id, headers = authed_user

    def profile_exists() -> bool:
        return _profile_exists(db_engine, user_id)

    movie_id = seeded_movies["inception_id"]

    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"status": "unwatched", "rating": None},
    )
    assert not profile_exists()

    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"status": "watched", "rating": 5},
    )
    assert profile_exists()

    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"status": "watched", "rating": 2},
    )
    assert not profile_exists()

    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"status": "watched", "rating": 5},
    )
    assert profile_exists()

    await client.put(
        f"/v1/users/{user_id}/ratings/{movie_id}",
        headers=headers,
        json={"status": "unwatched", "rating": None},
    )
    assert not profile_exists()


@pytest.mark.asyncio
async def test_dislike_penalizes_recommendations(
    client: AsyncClient, db_engine, embedding_dim, authed_user
):
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

    user_id, headers = authed_user

    def vec(x0: float, x1: float) -> list[float]:
        values = [0.0] * embedding_dim
        values[0] = x0
        values[1] = x1
        return values

    inv_sqrt2 = 1.0 / math.sqrt(2.0)

    anchor_id = 2000
    candidate_a_id = 2001
    candidate_b_id = 2002

    dislike_ids = [2100 + idx for idx in range(DISLIKE_MIN_COUNT)]

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

    await client.put(
        f"/v1/users/{user_id}/ratings/{anchor_id}", headers=headers, json={"rating": 5}
    )

    def get_score(movie_id: int, recs: list[dict]) -> float:
        for item in recs:
            if item["id"] == movie_id:
                score = item.get("score")
                assert score is not None
                return float(score)
        raise AssertionError(f"movie_id {movie_id} not found in recommendations")

    # Baseline: A and B are symmetric around anchor => same score
    resp = await client.get(f"/v1/users/{user_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()["data"]
    score_a_base = get_score(candidate_a_id, recs)
    score_b_base = get_score(candidate_b_id, recs)
    assert score_a_base == pytest.approx(score_b_base, abs=1e-3)

    # Below threshold: still no penalty applied
    for dislike_id in dislike_ids[: max(DISLIKE_MIN_COUNT - 1, 0)]:
        await client.put(
            f"/v1/users/{user_id}/ratings/{dislike_id}", headers=headers, json={"rating": 1}
        )

    resp = await client.get(f"/v1/users/{user_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()["data"]
    score_a_mid = get_score(candidate_a_id, recs)
    score_b_mid = get_score(candidate_b_id, recs)
    assert score_a_mid == pytest.approx(score_b_mid, abs=1e-3)

    # Reach threshold: penalty should kick in
    if DISLIKE_MIN_COUNT > 0:
        await client.put(
            f"/v1/users/{user_id}/ratings/{dislike_ids[-1]}",
            headers=headers,
            json={"rating": 1},
        )

    resp = await client.get(f"/v1/users/{user_id}/recommendations", headers=headers)
    assert resp.status_code == 200
    recs = resp.json()["data"]
    score_a_final = get_score(candidate_a_id, recs)
    score_b_final = get_score(candidate_b_id, recs)

    # Candidate B is closer to dislikes, so it should be penalized more.
    min_expected_gap = max(0.01, DISLIKE_WEIGHT * 0.05)
    assert score_a_final > score_b_final + min_expected_gap
