# Sergeek Campaign Agent Dashboard

Analytics dashboard for the Beeline Tariff Marketing Campaigns Case. It presents campaign planning, agent evidence, local simulation stability and environment limits.

## Run locally

```bash
npm install
npm run dev
```

Build the production bundle:

```bash
npm run build
```

From the repository root, the complete dashboard and API can also be started
with Docker:

```bash
docker compose up -d --build frontend api
```

Open `http://localhost:5173`.

## Data connection

Русский интерфейс использует относительные запросы `/api/*`.
В Docker их перенаправляет Nginx, при `npm run dev` — Vite proxy
на `http://127.0.0.1:8000`. Оставьте `VITE_API_URL` пустым.
Для API на другом адресе можно указать его URL явно.
The service layer expects:

- `GET /api/dashboard`
- `GET /api/campaigns`
- `GET /api/pilots`
- `GET /api/simulations/latest`
- `POST /api/simulations/run`

When an API call is unavailable, the UI automatically uses typed demo data and displays a `Demo data` badge. Components access data only through `src/services/api.ts` and `src/hooks/useDashboard.ts`.

All displayed evaluation metrics are marked as local mock simulation and must not be interpreted as guaranteed production results.
