# Sergeek demo API

The API exposes the campaign agent to the presentation dashboard. All metrics
are produced by the organizer-provided local mock environment and are labelled
accordingly; they are not claims about the hidden judging model.

## Run with Docker

From the repository root:

```bash
docker compose up -d --build api
```

Open `http://localhost:8000/docs` for the interactive OpenAPI page.

## Endpoints

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/campaigns?seed=42`
- `GET /api/pilots?seed=42`
- `GET /api/simulations/latest`
- `POST /api/simulations/run` with `{"runs": 10, "seed_start": 0}`

Simulation runs are synchronous and intentionally capped at 100.
