# Taste-Kid Web

React + Tailwind + shadcn UI frontend for the Taste-Kid stack.

## Authentication

Authentication is handled via Keycloak (OIDC).

- The app redirects to Keycloak for login and registration.
- Local email/password auth is not used by the web UI.

### Build-time Variables

These variables must be available at build time (Vite bakes them into the bundle):

- `VITE_API_URL`: API base URL (the client appends `/v1`)
- `VITE_KEYCLOAK_ISSUER_URL`: Keycloak realm issuer URL (example: `http://localhost:8080/realms/taste-kid`)
- `VITE_KEYCLOAK_CLIENT_ID`: Keycloak client ID (example: `taste-kid-web`)

## Local development

```bash
cd apps/web
npm install
npm run dev
```

If you want to run the web app outside Docker, set:

```bash
export VITE_API_URL="http://localhost:8000"
export VITE_KEYCLOAK_ISSUER_URL="http://localhost:8080/realms/taste-kid"
export VITE_KEYCLOAK_CLIENT_ID="taste-kid-web"
```

## Docker

Build and run the container (Vite build + nginx):

```bash
docker build \
  --build-arg VITE_API_URL="http://localhost:8000" \
  --build-arg VITE_KEYCLOAK_ISSUER_URL="http://localhost:8080/realms/taste-kid" \
  --build-arg VITE_KEYCLOAK_CLIENT_ID="taste-kid-web" \
  -t taste-kid-web .

docker run -p 5173:80 taste-kid-web
```

## Recommendation data

- Feed/recommendation responses include an optional `score` when personalized reranking is applied.
- Ratings of 1-2 stars influence the personalized feed (penalized), while 3 stars is treated as neutral.
- The UI treats `score` as optional.

## Themes

Design tokens live in `src/index.css`. To switch to the graphite theme, add
`class="theme-graphite"` on the `html` element in `index.html`.
