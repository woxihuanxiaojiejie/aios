# AIOS Runtime Runbook

## Install

```bash
uv sync
npm install
```

Optional provider extras:

```bash
uv sync --extra market-data
uv sync --extra market-data-baostock
uv sync --extra llm
```

## Environment

Use `.env.example` as the template and keep real secrets in `.env`.

```bash
export AIOS_DATABASE_URL='postgresql+psycopg://aios:aios@localhost:5432/aios'
export AIOS_CORS_ORIGINS='http://127.0.0.1:5173,http://localhost:5173'
export VITE_API_BASE_URL='http://127.0.0.1:8000/api/v1'
```

Real LLM smoke is opt-in:

```bash
export AIOS_RUN_EXTERNAL_LLM_TESTS=1
export AIOS_EXTERNAL_LLM_MODEL='deepseek/deepseek-chat'
export DEEPSEEK_API_KEY='...'
```

## PostgreSQL

Start PostgreSQL with Docker Compose:

```bash
docker compose up -d postgres
```

Upgrade schema:

```bash
uv run alembic upgrade head
```

Check migration heads:

```bash
uv run alembic heads
uv run alembic current
```

Backup:

```bash
docker compose exec -T postgres pg_dump -U aios -d aios > aios-backup.sql
```

Restore:

```bash
docker compose exec -T postgres psql -U aios -d aios < aios-backup.sql
```

## API

Run the API:

```bash
uv run uvicorn aios.api.app:create_default_app --factory --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
```

## Scheduler

The scheduler is a separate process. It registers only two fixed APScheduler
jobs: `research_due_scan` and `settlement_due_scan`. Watchlist and business
records in PostgreSQL are the only business fact source.

Run continuously:

```bash
uv run aios scheduler serve
```

Run one scan:

```bash
uv run aios scheduler run-once
```

Run only settlement due scan:

```bash
uv run aios settlement run-once
```

Optional intervals:

```bash
export AIOS_RESEARCH_SCAN_INTERVAL_SECONDS=300
export AIOS_SETTLEMENT_SCAN_INTERVAL_SECONDS=300
export AIOS_SCHEDULER_TZ=UTC
```

Stop safely with `Ctrl+C` or `SIGTERM`.

While running, `uv run aios scheduler serve` writes a minimal heartbeat to
PostgreSQL and records safe summaries for the two fixed jobs. The read-only
`GET /api/v1/system/status` endpoint reports scheduler `healthy` when the last
heartbeat is no older than three times the largest configured scan or misfire
interval. If the heartbeat is older, scheduler status is `unavailable`; if no
heartbeat has ever been recorded, status is `unknown`.

Provider status on `/system` uses local configuration validation only. It does
not call external LLM providers and never returns API keys, tokens, database
URLs, authorization headers, or raw provider responses.

## Frontend

Run local dev server:

```bash
npm run dev
```

Build and preview:

```bash
npm run build
npm run preview
```

## Docker Compose

Run the full stack:

```bash
docker compose up --build postgres backend scheduler frontend
```

Expected services:

```text
postgres
backend
scheduler
frontend
```

Do not start old containers from prior project versions. Check and remove stale
containers by project name only after confirming they are unrelated:

```bash
docker compose ps
docker ps --format '{{.Names}}\t{{.Ports}}'
```

Port checks:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/research/watchlist
```

## Watchlist And Research

Add a Watchlist item:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/v1/research/watchlist \
  -H 'content-type: application/json' \
  -d '{"symbol":"600519","market":"CN","note":"runtime smoke"}'
```

Enable auto research on an item:

```bash
curl -fsS -X PATCH http://127.0.0.1:8000/api/v1/research/watchlist/wl_xxx \
  -H 'content-type: application/json' \
  -d '{"auto_research_enabled":true,"research_horizon_days":3,"schedule_time":"15:00:00","schedule_timezone":"Asia/Shanghai"}'
```

Manually run research:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/v1/research/watchlist/wl_xxx/run
```

Run due scans:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/v1/research/scheduler/run-once
curl -fsS -X POST http://127.0.0.1:8000/api/v1/research/settlement/run-once
```

View records:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/research/runs/run_xxx
curl -fsS http://127.0.0.1:8000/api/v1/research/trade-plans/tp_xxx
curl -fsS http://127.0.0.1:8000/api/v1/research/simulated-executions/se_xxx
curl -fsS 'http://127.0.0.1:8000/api/v1/research/history?symbol=600519'
```

Failed research runs keep `failed_stage`, `error_type`, and `error` on
ResearchRun. Settlement errors are returned by the settlement scan endpoint and
stored by the underlying settlement lifecycle when a settlement record is
created.

Retry by fixing the provider or LLM error and running:

```bash
uv run aios scheduler run-once
uv run aios settlement run-once
```

## Verification

Offline deterministic tests:

```bash
uv run pytest -q
```

Static checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
git diff --check
```

Frontend:

```bash
npm test
npm run typecheck
npm run build
```

External smoke tests are opt-in and skip by default without keys:

```bash
uv run pytest tests/external -q
AIOS_RUN_EXTERNAL_LLM_TESTS=1 uv run pytest -m external_llm -q
```
