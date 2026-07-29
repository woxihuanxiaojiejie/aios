# BRAIN-001 — Evidence Engine

## Core Question

What happened?

## Responsibility

Collect, normalize, classify and evaluate all market evidence.

## Inputs

- Market Data
- Technical Indicators
- Capital Flow
- Financial Reports
- Company Announcements
- News
- Government Policies
- Macro Economic Data
- Historical Knowledge

## Outputs

- Evidence Set
- Evidence Graph
- Evidence Timeline
- Evidence Score

## Responsibilities

- Collect evidence
- Normalize data
- Remove duplicates
- Classify evidence
- Evaluate evidence quality
- Build relationships between evidence
- Provide evidence to downstream modules

## Does NOT

- Generate hypotheses
- Analyze stocks
- Make trading decisions

## Implementation Order

AIOS must prefer mature open-source components before adding original
collection, retry, cache, parsing, scheduling, or deduplication code.

### Open-Source Reuse Inventory

| Capability | Reuse decision | Component |
| --- | --- | --- |
| News collection | Needs adapter | `feedparser` RSS feeds first |
| RSS subscription | Direct reuse | `feedparser` |
| Web article extraction | Needs adapter | `trafilatura` |
| Listed-company announcements | Needs adapter | AKShare CNInfo/Eastmoney APIs |
| Financial report data | Needs adapter | AKShare/BaoStock financial APIs |
| Market data | Already integrated | AKShare and BaoStock |
| HTTP retry | Direct reuse | `tenacity` |
| Rate limiting | Direct reuse | `pyrate-limiter` |
| HTTP caching | Direct reuse | `requests-cache` |
| Content deduplication | Needs adapter | deterministic exact matching only; no semantic deduplication |
| Scheduling | Deferred | no scheduler is needed for the current manual intake workflow |
| Data validation | Already integrated | Pydantic |

### Component Intake Rule

Integrate one mature component per commit. Each component must document its
install method, configuration, minimal call entry, real-data test, failure
handling, and source trace fields.

### Current Component: RSS News via feedparser

- Install: runtime dependency `feedparser>=6.0,<7`.
- Configuration: feed URL and `source_id`; no secrets required.
- Minimal entry: `FeedparserRSSAdapter().fetch(feed_url=..., source_id=...)`.
- Real-data test: `AIOS_RUN_EXTERNAL_NEWS_TESTS=1 uv run pytest tests/external/test_external_news_rss_smoke.py -q -s`.
- Raw retention: writes RSS XML and pre-normalized `feedparser` entries under
  `results/brain001/rss/`.
- Failure handling: `fetch_many()` records per-provider errors without failing
  the whole batch.
- Source trace: each item keeps `provider_name`, `feed_url`, `source_id`,
  `entry_id`, and `entry_link`.

### Current Component: Webpage Text via trafilatura

- Install: runtime dependency `trafilatura>=2,<3`.
- Configuration: page URL and `source_id`; no secrets required.
- Minimal entry: `TrafilaturaWebpageAdapter().fetch(page_url=..., source_id=...)`.
- Real-data test: `AIOS_RUN_EXTERNAL_NEWS_TESTS=1 uv run pytest tests/external/test_external_webpage_extraction_smoke.py -q -s`.
- Raw retention: writes HTML and trafilatura JSON payload under
  `results/brain001/webpage/`.
- Failure handling: `fetch_many()` records per-page errors without failing the
  whole batch.
- Source trace: each result keeps `provider_name`, `page_url`, `source_id`,
  `hostname`, and trafilatura `fingerprint` when available.

### Current Component: CNInfo Announcements via AKShare

- Install: existing optional dependency group `market-data`
  (`uv sync --extra market-data` or `uv run --extra market-data ...`).
- Configuration: symbol, market, category, and date range; no secrets required.
- Minimal entry: `AKShareAnnouncementsAdapter().fetch_cninfo_disclosures(...)`.
- Real-data test: `AIOS_RUN_EXTERNAL_MARKET_TESTS=1 uv run --extra market-data pytest tests/external/test_external_akshare_announcements_smoke.py -q -s`.
- Raw retention: writes AKShare provider rows under
  `results/brain001/announcements/`.
- Failure handling: `fetch_many_cninfo_disclosures()` records per-symbol errors
  without failing the whole batch.
- Source trace: each item keeps `provider_name`, `source_function`, `symbol`,
  `announcement_url`, and `announcement_time`.

### Current Component: HTTP Retry via tenacity

- Install: runtime dependency `tenacity>=8,<10`.
- Configuration: retry attempts and fixed wait seconds at the HTTP fetcher
  boundary.
- Minimal entry: `RetryingHTTPFetcher(fetch_once, attempts=3).fetch(url)`.
- Real-data test: rerun RSS/webpage external smoke through their default HTTP
  clients.
- Failure handling: exhausted retries re-raise the provider error so adapters
  can record per-source failures.
- Source trace: preserved by the calling source adapter; retry does not mutate
  provider metadata.

### Current Component: HTTP Cache via requests-cache

- Install: runtime dependency `requests-cache>=1.2,<2`.
- Configuration: `HTTPClientConfig(cache_enabled=..., cache_name=..., expire_after_seconds=...)`.
- Default expiration: `DEFAULT_CACHE_EXPIRE_SECONDS` in the HTTP runtime layer.
- Runtime files: default SQLite cache path under `runtime/brain001/`, ignored by Git.
- Minimal entry: `RequestsHTTPClient(config=...).fetch_response(url)`.
- Real-data test: RSS and webpage smoke each fetch twice with cache enabled and
  assert the second response reports `from_cache=True`.
- Failure handling: cache session setup failure falls back to uncached
  `requests.Session`.
- Source trace: RSS/webpage result exposes `response_from_cache`; raw artifact
  saving remains unchanged.

### Current Component: Provider Rate Limiting via pyrate-limiter

- Install: runtime dependency `pyrate-limiter>=3,<5`.
- Configuration: per-provider `ProviderRateLimitConfig(max_requests, window_seconds, wait_strategy, timeout_seconds)`.
- Minimal entry: `ProviderRateLimiter({"rss": ProviderRateLimitConfig(...)}).acquire("rss")`.
- Boundary: `RequestsHTTPClient` acquires a permit immediately before each
  external request attempt.
- Retry order: tenacity wraps the single-attempt function, so every retry calls
  rate limiting again before the provider request.
- Failure handling: fail-fast configs raise `ProviderRateLimitExceeded`;
  waiting configs delegate waiting to pyrate-limiter.

### Current Component: Stable Content Fingerprints via hashlib

- Install: Python standard library only.
- Configuration: none.
- Minimal entry: `content_fingerprint(text)`.
- Normalization: Unicode NFC, trim leading/trailing whitespace, collapse
  consecutive whitespace including newline differences to one space.
- Preserved content: punctuation, digits, case, and all non-whitespace text are
  not removed or rewritten.
- Output: SHA-256 lowercase hex digest.
- Scope: provider outputs may carry `fingerprint`; no repository, automatic
  duplicate dropping, cross-source merge, fuzzy matching, embeddings, or
  semantic deduplication.

### Current Component: Provider Intake Validation via Pydantic

- Install: existing Pydantic 2.x dependency.
- Scope: pre-normalized provider records only; no final Evidence model or
  repository.
- Models: `RSSIntakeRecord`, `WebpageIntakeRecord`, and
  `AnnouncementIntakeRecord`.
- Common fields: `source`, `source_type`, `source_url` or `source_identifier`,
  `published_at`, `collected_at`, `raw_artifact_path`, `title`, `summary`,
  `content`, and `fingerprint`.
- Missing source data: nullable fields remain `None`; adapters do not invent
  provider facts.
- Failure handling: invalid provider records raise clear adapter errors after
  raw and pre-normalized artifacts are preserved.

### Current Component: Unified Evidence Model

- Module: `aios.integrations.evidence`; this is the BRAIN-001 intake Evidence
  contract and does not replace the existing decision-lifecycle Kernel model.
- Minimal entries: `evidence_from_rss()`, `evidence_from_webpage()`, and
  `evidence_from_announcement()`.
- Traceability: core fields remain queryable; the validated Provider record and
  raw artifact path are retained unchanged.
- Point-in-Time: all datetimes are timezone-aware UTC values and
  `available_at >= collected_at`; missing provider publication times remain
  `None`.

### Current Component: Evidence Repository

- Storage: existing PostgreSQL, SQLAlchemy, JSONB, and Alembic systems.
- Migration: `0011_brain_evidence` adds the `brain_evidence` table without
  changing the historical Kernel `evidence` table or previous migrations.
- Operations: create, get by UUID, fingerprint existence, source listing,
  availability cutoff listing, time-range listing, and filtered queries.
- Transaction boundary: one Evidence create is committed atomically; failed
  writes are rolled back and never trigger Provider calls.

### Current Component: Exact Evidence Deduplication

- Module: `aios.integrations.evidence_deduplication`.
- Rules: same source and identifier reports duplicate or revision; equal
  fingerprints across sources or identifiers report an exact duplicate
  candidate.
- Policy: every result includes the matched ID, fingerprint, and rule name;
  candidates are always preserved. No title-only, URL-only, fuzzy, semantic,
  embedding, vector, or LLM deduplication is implemented.

### Current Component: Evidence Query API

- Endpoint: `GET /api/v1/brain/evidence` and
  `GET /api/v1/brain/evidence/{evidence_id}`.
- Queries: source, source type, fingerprint, published/collected ranges,
  `as_of` availability cutoff, pagination, and timestamp sorting.
- Trace fields: Provider record, metadata, and raw artifact path are omitted by
  default and included only when explicitly requested.
- Runtime boundary: read-only Repository access; no collection, LLM, or
  downstream Brain module is triggered.

### Scheduling Evaluation

The repository has no mature scheduling or task-runner dependency. APScheduler
is intentionally deferred: current Provider adapters and their real-data smoke
checks are manually invokable, while Provider contracts, Point-in-Time queries,
and failure boundaries have just stabilized. A later scheduling task should
first define re-entry locking, run-state persistence, and per-Provider failure
isolation before selecting a scheduler.
