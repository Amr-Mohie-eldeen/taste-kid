# Taste‑Kid API

FastAPI service powering search, similarity, and personalized recommendations.

## Overview

The API exposes endpoints for:

- Movie lookup and details
- Similar movies by vector distance
- User profile creation
- Ratings and profile recompute
- Feed and recommendations

Core entrypoint: `apps/api/src/api/main.py`.

## Search + Similarity Flow

```mermaid
flowchart TD
    A["Title Search Request"] --> B["GET /movies/lookup"]
    B --> C{"Movie Found?"}
    C -- "No" --> D["404 Movie not found"]
    C -- "Yes" --> E["Movie ID"]
    E --> F["GET /movies/{id}"]
    E --> G["GET /movies/{id}/similar"]
    G --> H["Candidate fetch (K)"]
    H --> I{"Re-rank enabled?"}
    I -- "No" --> J["Return top-N by distance"]
    I -- "Yes" --> K["Apply re-rank model"]
    K --> L["Return top-N by score"]
```

## Re-ranking

Re-ranking improves candidate ordering after the initial vector similarity pass.

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Similarity as Similarity Engine
    participant Rerank as Rerank Model

    Client->>API: GET /movies/{id}/similar
    API->>Similarity: Fetch top-K candidates
    Similarity-->>API: K candidates (distance)
    API->>Rerank: Apply rerank(anchor, candidates)
    Rerank-->>API: Scored top-N
    API-->>Client: List of similar movies
```

### Key settings

- `SIM_CANDIDATES_K`: initial candidate pool size
- `SIM_TOP_N`: final number returned
- `SIM_RERANK_ENABLED`: enable re-ranking

## Recommendations + Feed

- **Recommendations**: top‑N by similarity to user profile embedding.
- **Feed**: if user has a profile, same as recommendations; otherwise falls back to popularity‑based queue.

## Local Development

Run the full stack via Docker Compose at repo root:

```bash
make build
```

API docs: http://localhost:8000/docs
