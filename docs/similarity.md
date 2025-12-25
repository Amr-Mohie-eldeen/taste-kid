# Similarity + Reranking Contract

## Fields used for reranking

- `genres`
- `keywords`
- `runtime`
- `release_date`
- `original_language`
- `vote_count`
- `vote_average`

## Style keywords

Style keywords are a curated subset of `keywords` that describe film form or tone rather than plot
entities. Examples include: neo-noir, whodunit, reverse chronology, nonlinear timeline,
psychological thriller, mind-bending, unreliable narrator, twist ending, time loop, and found
footage.

The allowlist lives in `apps/api/src/api/rerank/style_keywords.py` and can be edited without
touching scoring code.

## Not used for reranking

The reranker ignores fields like `budget`, `revenue`, `poster_path`, `backdrop_path`,
`production_companies`, `production_countries`, and `homepage`.
