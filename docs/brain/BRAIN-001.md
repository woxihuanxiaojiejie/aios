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
| Content deduplication | Needs adapter | exact hash first, `datasketch` for near-duplicates |
| Scheduling | Direct reuse | APScheduler |
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
