# AIOS

AIOS is an AI Decision Operating System. V0.1 implements only the minimal
decision lifecycle kernel:

```text
Evidence -> Experiment -> Decision -> Review -> Learning
```

This repository is intentionally narrow. It does not include broker
integrations, real order placement, RAG frameworks, backtesting engines, or
Learning automation. PostgreSQL is the durable business store. APScheduler is
used only by the standalone scheduler process to wake two fixed scan services;
per-symbol research state remains in Watchlist, ResearchRun, SimulatedExecution,
Settlement, and idempotent business records. AKShare and BaoStock support are
independent market-data providers that use the same `MarketDataAdapter` protocol
to import A-share daily bars as `Evidence`.

The HTTP API is currently intended only for local development and trusted
networks. Do not expose it directly to the public internet.

## Requirements

- Python 3.12
- uv
- PostgreSQL for the persistent storage adapter
- Docker for PostgreSQL integration tests through testcontainers

## Setup

```bash
uv sync
```

Install optional market-data dependencies only when using those providers:

```bash
uv sync --extra market-data
uv sync --extra market-data-baostock
uv sync --extra llm
```

For PostgreSQL storage, configure:

```bash
export AIOS_DATABASE_URL=postgresql+psycopg://localhost:5432/aios
```

Use `.env.example` as the local template. Do not commit `.env`.

## Testing

Run unit and in-memory tests:

```bash
uv run pytest tests/unit -q
```

Run PostgreSQL integration tests with Docker available:

```bash
uv run pytest tests/integration -q
```

The test suite includes unit coverage for entity validation, storage behavior,
mapper round trips, database exception mapping, PostgreSQL constraints, Alembic
migrations, market-data mapping, and full lifecycle persistence. Default tests
use fakes for AKShare and BaoStock and do not access the public network.
Coverage must stay at or above 90%.

## Migrations

Apply and roll back the PostgreSQL schema with Alembic:

```bash
uv run alembic upgrade head
uv run alembic downgrade base
```

Alembic reads `AIOS_DATABASE_URL` unless `sqlalchemy.url` is provided directly.
The application does not create tables at import or startup.

## Quality Checks

Run the full local gate before committing:

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
uv run pytest --cov=aios --cov-report=term-missing --cov-fail-under=90
```

## HTTP API

Run the API against PostgreSQL:

```bash
export AIOS_DATABASE_URL='postgresql+psycopg://localhost:5432/aios'
uv run alembic upgrade head
uv run uvicorn aios.api.app:create_default_app --factory
```

For local development with in-memory storage, use an explicit factory:

```bash
uv run python -c "import uvicorn; from aios.api.app import create_app; from aios.storage.memory import InMemoryStorage; uvicorn.run(create_app(storage=InMemoryStorage()))"
```

Available routes:

```text
GET  /health
GET  /api/v1/health
POST /api/v1/evidence
GET  /api/v1/evidence
GET  /api/v1/evidence/{evidence_id}
POST /api/v1/experiments
GET  /api/v1/experiments
GET  /api/v1/experiments/{experiment_id}
POST /api/v1/experiments/{experiment_id}/complete
POST /api/v1/decisions
GET  /api/v1/decisions
GET  /api/v1/decisions/{decision_id}
POST /api/v1/reviews
GET  /api/v1/reviews
GET  /api/v1/reviews/{review_id}
POST /api/v1/learnings
GET  /api/v1/learnings
GET  /api/v1/learnings/{learning_id}
POST /api/v1/learnings/{learning_id}/approve
POST /api/v1/learnings/{learning_id}/reject
POST /api/v1/market-data/akshare/daily-bars/preview
POST /api/v1/market-data/akshare/daily-bars/import
POST /api/v1/market-data/baostock/daily-bars/preview
POST /api/v1/market-data/baostock/daily-bars/import
POST /api/v1/decision-generation/generate
POST /api/v1/research/watchlist
GET  /api/v1/research/watchlist
GET  /api/v1/research/watchlist/{item_id}
PATCH /api/v1/research/watchlist/{item_id}
POST /api/v1/research/watchlist/{item_id}/archive
POST /api/v1/research/watchlist/{item_id}/restore
POST /api/v1/research/watchlist/{item_id}/run
POST /api/v1/research/scheduler/run-once
POST /api/v1/research/settlement/run-once
GET  /api/v1/research/market
POST /api/v1/research/evidence
POST /api/v1/research/experiments
POST /api/v1/research/decisions
POST /api/v1/research/settlements/{decision_id}
GET  /api/v1/research/history
```

Run the standalone scheduler process against PostgreSQL:

```bash
uv run aios scheduler serve
```

Run one due scan manually:

```bash
uv run aios scheduler run-once
uv run aios settlement run-once
```

List endpoints support `limit` and `offset`. `limit` defaults to 50 and is capped
at 200.

### AKShare Market Data

The AKShare adapter wraps only `akshare.stock_zh_a_hist` for A-share daily bars.
API symbols must use the `000001.SZ` or `600000.SH` form. Supported adjustments
are `none`, `qfq`, and `hfq`.

Preview standardized bars without writing storage:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/market-data/akshare/daily-bars/preview \
  -H 'content-type: application/json' \
  -d '{"symbol":"000001.SZ","start_date":"2026-07-01","end_date":"2026-07-18","adjustment":"qfq"}'
```

Import bars as `Evidence` through the existing lifecycle service:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/market-data/akshare/daily-bars/import \
  -H 'content-type: application/json' \
  -d '{"symbol":"000001.SZ","start_date":"2026-07-01","end_date":"2026-07-18","adjustment":"qfq"}'
```

AKShare is used here for research data ingestion. Its upstream interface can
change, and historical responses are not strict point-in-time datasets. In the
current environment, a real AKShare smoke call failed with an upstream
connection close from the Eastmoney path; this does not indicate an AIOS Kernel
failure.

### BaoStock Market Data

The BaoStock adapter wraps only `login()`, `query_history_k_data_plus(...)`, and
`logout()` for A-share daily bars. API symbols use the same `000001.SZ` or
`600000.SH` form and are mapped to BaoStock codes such as `sz.000001` and
`sh.600000`.

Preview standardized BaoStock bars:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/market-data/baostock/daily-bars/preview \
  -H 'content-type: application/json' \
  -d '{"symbol":"000001.SZ","start_date":"2026-07-13","end_date":"2026-07-17","adjustment":"none"}'
```

Import BaoStock bars as `Evidence`:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/market-data/baostock/daily-bars/import \
  -H 'content-type: application/json' \
  -d '{"symbol":"000001.SZ","start_date":"2026-07-13","end_date":"2026-07-17","adjustment":"qfq"}'
```

Imported market-data metadata records
`historical_point_in_time_guarantee: false`. Data source availability or
upstream failure is separate from AIOS Kernel correctness, and these interfaces
must not be used directly for live trading decisions.

### LLM Decision Generation

The LLM boundary uses LiteLLM as an in-process SDK only. AIOS does not deploy a
LiteLLM proxy, implement provider SDK adapters, or route models. The Kernel does
not import LiteLLM.

Create an Experiment with:

- `model`: a LiteLLM model name such as `openai/...`, `deepseek/...`, or another
  provider/model configured by LiteLLM.
- `prompt_version`: `decision-v1`
- `evidence_ids`: existing Evidence IDs to provide to the model.
- `parameters`: only `temperature` is read, and it must be between `0` and `1`.

Provider API keys are read by LiteLLM from the provider's standard environment
variables. Do not put API keys in Experiment parameters, database rows, or API
requests.

Generate a Decision:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/decision-generation/generate \
  -H 'content-type: application/json' \
  -d '{"experiment_id":"ex_xxx","symbol":"000001.SZ","horizon":"1d"}'
```

The prompt is built by `decision-v1` code, not by the router. It serializes only
the Experiment request context and provided Evidence, with stable ordering and
bounded size. The model must return a structured `DecisionDraft`; AIOS validates
that draft with Pydantic and then validates the resulting `Decision` through the
existing lifecycle service. LLM output must pass domain validation, but domain
validation cannot prove the investment conclusion is correct.

`valid_until` uses natural time, for example `created_at + 1 day` for `1d`. AIOS
does not use a trading calendar in V0.1. Repeated `POST generate` calls can
create multiple Decisions because API idempotency is deferred.

For PostgreSQL storage, bounded generation metadata is saved in
`llm_generation_records`: decision ID, experiment ID, provider, model, prompt
version, prompt hash, Evidence snapshot hash, temperature, token counts, latency,
and creation time. AIOS does not save API keys, hidden reasoning, full prompts,
or full provider responses.

Default tests do not call model providers. Optional real smoke:

```bash
export AIOS_RUN_EXTERNAL_LLM_TESTS=1
export AIOS_EXTERNAL_LLM_MODEL='openai/...'
uv sync --extra llm --extra market-data-baostock
uv run pytest tests/external/test_external_llm_smoke.py -q
```

The smoke uses BaoStock Evidence and the configured model. It reports test
status only; it does not print API keys, full prompts, or hidden reasoning.
Current Decisions cannot directly trigger trades.

## Research Workbench

The browser workbench is available at `/research`. It calls only the AIOS
backend; provider API keys stay in backend environment variables and are not
returned to the browser.

Configure `.env` from `.env.example`:

```bash
AIOS_DATABASE_URL=postgresql+psycopg://aios:aios@localhost:5432/aios
AIOS_EXTERNAL_LLM_MODEL=deepseek/deepseek-chat
DEEPSEEK_API_KEY=your-local-key
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Local development:

```bash
uv sync --extra llm --extra market-data-baostock
uv run alembic upgrade head
uv run uvicorn aios.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
npm install
npm run dev
```

Open `http://127.0.0.1:5173/research`.

Docker startup:

```bash
docker compose up --build
```

Open `http://127.0.0.1:4173/research`. In Compose mode the backend is published
at `http://127.0.0.1:8000/api/v1`, matching local development. Compose starts
PostgreSQL, applies Alembic migrations in the backend container, and serves the
built frontend.

If port 8000 is already occupied, identify the process before stopping it:

```bash
ss -ltnp
docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}\t{{.Image}}'
```

Only stop a process you recognize. For example, if an old local stack owns the
port, stop that specific container:

```bash
docker stop ai-quant-platform-v3-backend-1
```

Smoke-check the current backend before opening the workbench:

```bash
curl -i http://127.0.0.1:8000/api/v1/evidence
curl -i -X POST http://127.0.0.1:8000/api/v1/research/watchlist \
  -H 'content-type: application/json' \
  -d '{"symbol":"600519","market":"CN","note":"smoke"}'
```

The workbench displays `REAL MARKET DATA` and `REAL LLM` when it is using the
production path. A-share symbols use the existing BaoStock adapter format such
as `000001.SZ` or `600000.SH`. Unsupported markets return a backend error
instead of fixture data.

## Minimal Usage

```python
from datetime import UTC, datetime, timedelta

from aios.kernel.decision import Decision
from aios.kernel.enums import Action
from aios.kernel.evidence import Evidence
from aios.kernel.experiment import Experiment
from aios.kernel.learning import Learning
from aios.kernel.review import Review
from aios.storage.memory import InMemoryStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService

created_at = datetime.now(UTC)
service = DecisionLifecycleService(InMemoryStorage())

evidence = service.register_evidence(
    Evidence(
        evidence_type="filing",
        source="company-report",
        symbols=["NVDA"],
        published_at=created_at,
        available_at=created_at,
        summary="Updated revenue guidance",
        reliability=0.85,
        content_hash="hash-guidance",
    )
)

experiment = service.start_experiment(
    Experiment(
        name="guidance-check",
        model="model-v1",
        prompt_version="prompt-v1",
        agent_config_version="agent-config-v1",
        dataset_snapshot="snapshot-2026-07-19",
        evidence_ids=[evidence.evidence_id],
        started_at=created_at,
    )
)

decision = service.create_decision(
    Decision(
        experiment_id=experiment.experiment_id,
        symbol="NVDA",
        action=Action.BUY,
        horizon="5d",
        confidence=0.72,
        expected_return=0.04,
        max_expected_loss=0.02,
        evidence_ids=[evidence.evidence_id],
        reasoning_summary="Guidance improved while risk stayed bounded",
        valid_until=created_at + timedelta(days=5),
    )
)

review = service.create_review(
    Review(
        decision_id=decision.decision_id,
        actual_return=0.03,
        direction_correct=True,
        risk_limit_breached=False,
        outcome="profit",
        cause_tags=["guidance"],
        review_summary="Decision matched the evidence-backed thesis",
    )
)

learning = service.propose_learning(
    Learning(
        review_id=review.review_id,
        learning_type="agent_weight_update",
        target="guidance-signal-weight",
        before={"weight": 0.4},
        after={"weight": 0.45},
        reason="Profitable reviewed decision",
    )
)
```

## PostgreSQL Storage Usage

Run migrations first, then inject `PostgresStorage` into the same lifecycle
service:

```python
from aios.storage.postgres import PostgresStorage
from aios.workflows.decision_lifecycle import DecisionLifecycleService

storage = PostgresStorage()
service = DecisionLifecycleService(storage)
```

`PostgresStorage()` reads `AIOS_DATABASE_URL`. You can also pass a URL directly
for tests or local scripts:

```python
storage = PostgresStorage(
    "postgresql+psycopg://localhost:5432/aios"
)
```

## Structure

```text
src/aios/kernel/      Pydantic entities, enums, and domain errors
src/aios/adapters/    Protocol definitions
src/aios/application/ Market Evidence import service
src/aios/integrations/akshare/ AKShare client, adapter, and mapper
src/aios/storage/     In-memory and PostgreSQL storage adapters
src/aios/workflows/   Decision lifecycle orchestration
alembic/              PostgreSQL schema migration
docs/adr/             Architecture decision records
tests/unit/           Entity, mapper, storage, and workflow unit tests
tests/integration/    Lifecycle and PostgreSQL container integration tests
```
