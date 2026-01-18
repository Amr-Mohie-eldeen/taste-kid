# apps/web AGENTS

React/Vite + Tailwind + shadcn/ui frontend.

## Commands
- `npm install`
- `npm run dev`
- `npm run build` (runs `tsc -b` then `vite build`)

## Where To Look
- App entry: `apps/web/src/main.tsx`
- Routing + providers: `apps/web/src/App.tsx`
- API client (envelope parsing; appends `/v1`): `apps/web/src/lib/api.ts`
- React Query hooks (preferred fetch layer): `apps/web/src/lib/hooks.ts`
- Auth/session state: `apps/web/src/lib/store.ts`
- React Query defaults: `apps/web/src/lib/queryClient.ts`
- Theme tokens: `apps/web/src/index.css`

## Conventions
- Prefer `apps/web/src/lib/hooks.ts` over ad-hoc `fetch` in components.
- Keep API field names in `snake_case`.
- No ESLint/Prettier configured; match existing style.

## Env Notes
- API base URL: `VITE_API_URL` (client appends `/v1`).

## Anti-Patterns
- Don’t add new styling systems; stick to Tailwind + shadcn/ui.
- Avoid `any`; extend types near `apps/web/src/lib/api.ts`.
