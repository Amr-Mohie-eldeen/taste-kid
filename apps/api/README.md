# Taste‑Kid API

FastAPI service powering search, similarity, and personalized recommendations for movies.

## Overview

The API exposes endpoints for:

- Health checks
- Movie lookup and details
- Similar movies by vector distance
- User profile creation
- Ratings and profile recompute
- Rating queue and next-movie suggestions
- Feed and recommendations
- User/movie match scores

Core entrypoint: `apps/api/src/api/main.py`. All routes are mounted under `/v1`.

## Response Envelope + Pagination

All endpoints return a response envelope:

```json
{
  "data": {"...": "..."},
  "meta": {
    "next_cursor": "20",
    "has_more": true
  }
}
```

Pagination is offset-based using `cursor` (offset) and `k` (page size). The API fetches `k + 1` items to decide `has_more`.

## Search + Similarity Flow

```mermaid
flowchart TD
    A["Title Search Request"] --> B["GET /v1/movies/lookup"]
    B --> C{"Movie Found?"}
    C -- "No" --> D["404 Movie not found"]
    C -- "Yes" --> E["Movie ID"]
    E --> F["GET /v1/movies/{id}"]
    E --> G["GET /v1/movies/{id}/similar"]
    G --> H["Candidate fetch (K)"]
    H --> I{"Re-rank enabled?"}
    I -- "No" --> J["Return top-N by distance"]
    I -- "Yes" --> K["Apply heuristic re-rank"]
    K --> L["Return top-N by score"]
```

## Similarity + Re-ranking

Similarity search uses pgvector cosine distance (`<=>`) on `movie_embeddings.embedding`.
If the anchor movie has no embedding, the API returns `EMBEDDING_NOT_FOUND`.

Re-ranking is a deterministic heuristic (not an ML model). It combines:

- Cosine similarity (distance)
- Genre/style overlap
- Runtime + release-year proximity
- Language match
- Popularity quality via `vote_count`
- Penalty for tonal genre mismatch

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Similarity as Similarity Engine
    participant Rerank as Heuristic Re-ranker

    Client->>API: GET /v1/movies/{id}/similar
    API->>Similarity: Fetch top-K candidates
    Similarity-->>API: K candidates (distance)
    API->>Rerank: Apply score(anchor, candidates)
    Rerank-->>API: Scored + sorted top-N
    API-->>Client: List of similar movies
```

### Key settings

- `SIM_CANDIDATES_K`: initial candidate pool size
- `SIM_TOP_N`: final number returned
- `SIM_RERANK_ENABLED`: enable re-ranking

## Recommendations + Feed

- **Recommendations**: top‑N by similarity to user profile embedding.
- **Feed**: if user has a profile, same as recommendations; otherwise falls back to popularity‑based queue.

### User Embedding + Rating Effects

Ratings update the user profile embedding immediately.

- **Input set**: only `status = watched` with `rating >= 4` (liked movies).
- **Weighting**: each movie embedding is weighted by `rating / 5.0`.
- **Aggregation**: weighted average of liked embeddings = user profile vector.
- **Empty profile**: if no liked embeddings exist, the profile row is deleted.

Changing a rating from `>= 4` to `< 4`, or marking a movie as `unwatched`, removes it from the profile on the next recompute.

#### Worked Example (Weighted Average)

Assume 3 liked movies with 3‑dim embeddings (toy example for intuition):

- Movie A embedding = `[0.2, 0.6, 0.0]`, rating = 5 → weight = `1.0`
- Movie B embedding = `[0.4, 0.4, 0.2]`, rating = 4 → weight = `0.8`
- Movie C embedding = `[0.9, 0.1, 0.0]`, rating = 2 → **excluded** (rating < 4)

Weighted sum = `1.0*[0.2, 0.6, 0.0] + 0.8*[0.4, 0.4, 0.2]`
= `[0.2 + 0.32, 0.6 + 0.32, 0.0 + 0.16]`
= `[0.52, 0.92, 0.16]`

Total weight = `1.0 + 0.8 = 1.8`

User profile embedding = `[0.52/1.8, 0.92/1.8, 0.16/1.8]`
= `[0.289, 0.511, 0.089]`

That profile vector is then used for kNN search against `movie_embeddings`.

### Recommendation Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB as Postgres+pgvector

    Client->>API: PUT /v1/users/{id}/ratings/{movie_id}
    API->>DB: Upsert rating (watched/unwatched)
    API->>DB: Fetch liked embeddings (rating >= 4)
    API->>DB: Compute weighted average
    API->>DB: Upsert user_profiles embedding
    API-->>Client: {"status": "ok"}

    Client->>API: GET /v1/users/{id}/recommendations
    API->>DB: Load user_profiles.embedding
    DB-->>API: embedding vector
    API->>DB: kNN search in movie_embeddings
    API->>DB: Filter out recently rated/unwatched
    DB-->>API: ordered candidates (distance)
    API-->>Client: list of recommendations
```

## Endpoints (All Under `/v1`)

### Health

- `GET /health`

### Movies

- `GET /movies/lookup?title=...`
- `GET /movies/{movie_id}`
- `GET /movies/{movie_id}/similar?k=20&cursor=0`

### Users + Ratings

- `POST /users` (create user)
- `GET /users/{user_id}` (summary)
- `PUT /users/{user_id}/ratings/{movie_id}` (rate or set status)
- `POST /users/{user_id}/rate` (rate with body)
- `GET /users/{user_id}/ratings` (rated movies)
- `GET /users/{user_id}/rating-queue` (popularity-based queue)
- `GET /users/{user_id}/next` (next movie to rate)
- `GET /users/{user_id}/profile` (profile stats)
- `GET /users/{user_id}/recommendations`
- `GET /users/{user_id}/feed`
- `GET /users/{user_id}/movies/{movie_id}/match` (0–100 match score)

## Data Model

```mermaid
erDiagram
    movies ||--o{ movie_embeddings : "has"
    users ||--o{ user_movie_ratings : "rates"
    movies ||--o{ user_movie_ratings : "rated"
    users ||--o{ user_profiles : "profile"

    movies {
        bigint id PK
        text title
        text original_title
        date release_date
        text genres
        text keywords
        int runtime
        text original_language
        float vote_average
        bigint vote_count
        text poster_path
        text backdrop_path
    }

    movie_embeddings {
        bigint movie_id PK, FK
        vector(768) embedding
        text embedding_model
        text doc_hash
        timestamptz created_at
    }

    users {
        bigint id PK
        text display_name
        timestamptz created_at
    }

    user_movie_ratings {
        bigint user_id PK, FK
        bigint movie_id PK, FK
        int rating
        text status
        timestamptz created_at
        timestamptz updated_at
    }

    user_profiles {
        bigint user_id PK, FK
        vector(768) embedding
        text embedding_model
        int num_ratings
        timestamptz updated_at
    }
```

## ML/MLP Concepts (Grounded in This Service)

- **Embeddings**: Movies have precomputed vectors stored in `movie_embeddings`.
- **Similarity**: Uses cosine distance via pgvector. Smaller distance = more similar.
- **User profile**: Weighted average of liked movie embeddings (a centroid in embedding space).
- **Recommendations**: Nearest neighbors to the user centroid, excluding seen items.
- **Re-ranking**: Heuristic scoring on top of similarity; no learned model in API.
- **If you add an MLP**: Replace the heuristic with a trained scoring model that consumes engineered features or embeddings and outputs a relevance score.

## Local Development

Run the full stack via Docker Compose at repo root:

```bash
make build
```

API docs: http://localhost:8000/docs
