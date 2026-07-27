# AIOS Final Acceptance

Date: 2026-07-27

## Scope

This acceptance covers the current repository implementation against
`docs/aios_goal.txt` with a reuse-first runtime integration:

```text
Watchlist
-> Scheduler due scan
-> ResearchRuntimeService
-> ResearchRunner
-> BrainResearchPipeline
-> Evidence
-> Skill reports
-> Hypothesis
-> first-stage independent reports
-> second-stage discussion
-> Decision
-> TradePlan
-> SimulatedExecution
-> Settlement
-> Outcome
-> Evaluation
-> Review
-> Learning Proposal
```

## Runtime Architecture

- PostgreSQL Watchlist, ResearchRun, TradePlan, SimulatedExecution, Outcome,
  Evaluation, Review, and Learning records are the durable business fact source.
- APScheduler is used only in the standalone `aios scheduler serve` process.
- APScheduler registers two fixed in-memory jobs:
  - `research_due_scan`
  - `settlement_due_scan`
- No APScheduler persistent job store, Redis, RabbitMQ, Celery, RQ, Kafka, or
  worker platform is introduced.
- Manual research API and scheduled research both call `ResearchRuntimeService`.
- `BrainResearchPipeline` remains responsible for research, discussion, and
  decision. Simulated execution is orchestrated outside the BRAIN pipeline.
- Settlement scans use existing `SimulatedExecution` records and existing
  settlement services as the fact source.

## Reused Open Source

- APScheduler `>=3.11.3,<4`
  - Purpose: stable single-process wake-up scheduler.
  - License: MIT.
  - GitHub stars observed during audit: 7,578.
  - Integration: dependency plus `aios.application.scheduler_app`.
- pandas-market-calendars `>=5,<6`
  - Purpose: mature exchange calendar lookup for A-share trading-day scans.
  - License: MIT.
  - GitHub stars observed during audit: 986.
  - Integration: dependency plus thin `MarketTradingCalendar` adapter.

No third-party source code was copied. No open source framework replaced the
AIOS single-agent, multi-skill BRAIN model.

## Verification Commands

Baseline before changes:

```text
uv run pytest -q: 477 passed, 12 skipped, 1 warning
uv run ruff check .: passed
uv run ruff format --check .: passed
uv run mypy src: passed
git diff --check: passed
npm test: 9 passed, 1 skipped
npm run build: passed
```

Final verification is recorded in the task final report after execution.

## Acceptance Notes

- Default production research path enters `BrainResearchPipeline` through
  `ResearchRunner`.
- Five MVP skills remain in the default BRAIN chain.
- Decision creates TradePlan; only READY TradePlan creates SimulatedExecution.
- `NO_TRADE`, invalid, expired, and missing-data plans do not create fake
  simulated executions.
- Settlement produces Outcome, Evaluation, Review, and proposal-only Learning.
- Learning proposals are not automatically applied.
- Production paths do not create fake Evidence or use LLM-generated missing
  facts as Evidence.
- Real external provider and LLM smoke tests remain opt-in by environment
  variables and skip by default without network credentials.
