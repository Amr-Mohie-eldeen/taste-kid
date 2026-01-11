# Taste-kid Web

React + Tailwind + shadcn UI frontend for the taste.io clone.

## Local development

```bash
cd apps/web
npm install
npm run dev
```

Set the API base URL if your FastAPI instance is not running on `http://localhost:8000` (the client appends `/v1` automatically):

```bash
export VITE_API_URL="http://localhost:8000"
```

## Recommendation data

- Feed/recommendation responses include an optional `score` when personalized reranking is applied.
- Ratings of 1–2★ influence the personalized feed (penalized), while 3★ is treated as neutral.
- The UI treats `score` as optional and does not render it by default.

## Docker

Build and run the container (uses Vite build + nginx):

```bash
docker build --build-arg VITE_API_URL="http://localhost:8000" -t taste-kid-web .
docker run -p 5173:80 taste-kid-web
```

## Themes

Design tokens live in `src/index.css`. To switch to the graphite theme, add
`class="theme-graphite"` on the `html` element in `index.html`.
