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
