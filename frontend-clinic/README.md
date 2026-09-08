# frontend-clinic

Bounded context Muestras (clínico) — React 18 + Vite 5 + TypeScript 5 + TanStack Query + React Router 6 (ADR-0015).

## Quickstart

```bash
npm install
cp .env.example .env

# Demo sin backend (MSW intercepta /api/clinic/*)
npm run dev:msw

# Dev conectado a backend-clinic real (:8002)
npm run dev
```

Abrir http://localhost:5174/clinic/samples

## Tests

```bash
npm test              # correr una vez
npm run test:watch    # modo watch
npm run test:coverage # con reporte de cobertura (gate RN-09: 90/88/90/90)
```

## Estructura

- `src/clinic/api/` — clientes HTTP (`samplesClient.ts`, `authClient.ts`)
- `src/clinic/auth/` — `SessionProvider`, `useSession`, `RequireRole`
- `src/clinic/hooks/` — TanStack Query hooks
- `src/clinic/components/` — componentes de UI
- `src/clinic/pages/` — 4 páginas (Lista, Form, Detalle, Modo Degradado)
- `src/clinic/msw/` — mocks para demo y tests

## Notas

- Puerto `:5174` (ADR-0015 #2). El admin usa `:5173`.
- Auth con SimpleJWT propio, independiente del admin (`biomed.clinic.access` / `biomed.clinic.refresh`).
- El botón "Procesar" delega en `backend-clinic` (`:8002`), que a su vez llama al FastAPI clínico (`:8000`) vía `pipeline_client.py` con circuit breaker (RN-07).
