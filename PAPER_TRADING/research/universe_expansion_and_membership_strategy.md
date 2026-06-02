# Tracked-Universe Expansion and Membership-History Strategy

Prepared on 2026-06-02. This is a design proposal only. It does not add or
remove any ticker, change a signal, or alter a simulated portfolio.

## Objective

Expand the overall stock universe over time without losing the ability to
answer:

- when a ticker first became eligible for signal analysis
- why it was added
- which sector lists contained it on a given date
- which source or review decision caused a membership change
- whether a historical strategy result used only information available at the
  time

The system should favor additions. The variable portfolios already decide
whether a tracked stock has an actionable technical or news-assisted signal.
Removal should therefore be uncommon and should normally mean "stop scanning
this entity" rather than "sell this entity."

## Current Baseline

The current tracked universe is derived from `data/trades.csv`. Existing
research-oriented sector portfolios cover an unusually detailed semiconductor
supply chain:

- `raw-materials-specialty-gases`
- `silicon-wafers`
- `lithography`
- `photomasks-eda`
- `deposition-etch`
- `cmp-cleaning-metrology`
- `advanced-packaging`
- `leading-edge-logic-foundry`
- `memory`
- `chip_design`

The repository already caches stock-level Alpaca and GDELT news snapshots.
YouTube search is optional when `YOUTUBE_API_KEY` is configured.

The next version should separate three concepts that currently overlap:

1. **Overall tracked universe**: tickers eligible for signals and news
   enrichment.
2. **Theme memberships**: a ticker may belong to zero, one, or several sector
   lists.
3. **Simulated portfolios**: trades created by explicit research lists or
   variable-strategy rules.

A ticker can be tracked without being purchased.

## Recommended Data Model

Do not use simulated trades as the permanent source of truth for universe
membership. Add append-only files or equivalent database tables.

### `data/entities.csv`

One row per security:

| Field | Purpose |
| --- | --- |
| `entity_id` | Stable internal ID |
| `ticker` | Canonical tracked ticker |
| `company_name` | Canonical company name |
| `security_type` | `stock`, `etf`, `crypto`, or other supported type |
| `exchange` | Primary listing venue when known |
| `country` | Issuer or primary-listing country |
| `aliases` | Name and ticker aliases used for news matching |
| `status` | `active`, `acquired`, `delisted`, `unsupported`, or `archived` |
| `created_at` | First recorded timestamp |

### `data/universe_membership_events.csv`

Append-only overall-universe history:

| Field | Purpose |
| --- | --- |
| `event_id` | Stable event ID |
| `effective_at` | Timestamp when the event becomes usable |
| `ticker` | Canonical ticker |
| `action` | `add`, `remove`, `restore`, or `archive` |
| `reason_code` | For example `manual`, `news-discovery`, `sector-seed`, `listing-change` |
| `source_url` | Primary supporting link when applicable |
| `score` | Discovery score at the time |
| `review_status` | `proposed`, `approved`, or `rejected` |
| `notes` | Human-readable rationale |

### `data/list_membership_events.csv`

Append-only individual-list history:

| Field | Purpose |
| --- | --- |
| `event_id` | Stable event ID |
| `effective_at` | Timestamp when the event becomes usable |
| `list_name` | Sector or research-list name |
| `ticker` | Canonical ticker |
| `action` | `add` or `remove` |
| `reason_code` | Manual, discovered, reclassified, or archived |
| `source_url` | Supporting link |
| `review_status` | Proposed, approved, or rejected |
| `notes` | Explanation |

### `data/discovery_candidates.csv`

Candidate queue, not an automatic portfolio:

| Field | Purpose |
| --- | --- |
| `candidate_id` | Stable candidate ID |
| `first_seen_at` | First discovery timestamp |
| `last_seen_at` | Latest supporting observation |
| `ticker` | Resolved ticker when known |
| `company_name` | Resolved or extracted company name |
| `sector_tags` | Candidate sectors |
| `discovery_sources` | Alpaca, GDELT, SEC, Nasdaq, YouTube, or manual |
| `mention_metrics` | Current and baseline counts |
| `score` | Ranked promotion score |
| `status` | `new`, `monitor`, `review`, `approved`, `rejected`, or `expired` |
| `evidence_urls` | Links used for review |

### Daily snapshots

Store dated snapshots of:

- overall tracked universe
- memberships by list
- candidate queue and scores
- news and video metrics used by the scorer
- deterministic promotion and removal recommendations

Snapshots are required for honest backtests. A ticker discovered on June 2
must not appear in a January strategy simulation unless a January snapshot
proves that it was discoverable then.

## Sector Taxonomy

Keep the existing semiconductor supply-chain categories. Add adjacent sectors
that reflect recurring AI-infrastructure bottlenecks and the current research
direction.

| Proposed sector | Why track it | Example discovery keywords |
| --- | --- | --- |
| `optical-networking-interconnects` | AI clusters depend on optical modules, switching, DSPs, and high-speed interconnects | optical transceiver, silicon photonics, coherent optics, 800G, 1.6T, AI networking |
| `data-center-power-cooling` | AI compute growth is constrained by power delivery, UPS systems, cooling, and thermal management | liquid cooling, data-center cooling, UPS, power distribution, thermal management |
| `grid-electrification` | Data centers and reshoring increase demand for transformers, switchgear, transmission, and grid equipment | transformer backlog, switchgear, transmission, grid modernization, electrification |
| `energy-for-data-centers` | Power procurement is increasingly linked to gas, nuclear, storage, and renewables | data-center power agreement, nuclear restart, small modular reactor, battery storage |
| `ai-cloud-data-center-operators` | Capacity providers can capture demand before or alongside chip suppliers | GPU cloud, AI cloud, colocation, hyperscale capacity, data-center lease |
| `cybersecurity-ai-infrastructure` | AI and cloud expansion increases security spending and creates new platform risks | cloud security, identity security, AI security, zero trust |
| `quantum-computing` | Already present informally through names such as `QBTS`; it should become an explicit theme | quantum annealing, trapped ion, quantum networking, quantum contract |
| `space-defense-autonomy` | Existing names such as `RKLB`, `RDW`, `SPIR`, and `SIDU` fit a common catalyst-driven group | satellite constellation, launch backlog, defense contract, autonomous systems |
| `robotics-industrial-automation` | AI adoption can produce second-order demand in sensors, machine vision, and industrial automation | robotics, warehouse automation, machine vision, industrial AI |
| `critical-minerals-energy-materials` | This extends the existing semiconductor raw-material thesis into power and strategic inputs | copper, uranium, rare earth, graphite, lithium, gallium, germanium |

Do not create a sector merely because one stock had a large return. Add a
sector when it represents a repeatable business bottleneck, demand chain, or
catalyst class.

## Free Discovery Sources

### Tier 1: use first

1. **GDELT DOC API**
   - Use sector-keyword queries to discover articles and company names beyond
     the current ticker list.
   - GDELT supports full-text public-news discovery, JSON output, date windows,
     and keyword operators.
   - Treat it as best effort: cache results, use delays, and tolerate
     throttling.

2. **Alpaca historical news**
   - Use Alpaca after a ticker is resolved or when scanning known securities.
   - It provides structured historical stock and crypto news dating back to
     2015.
   - Alpaca is stronger for known-symbol enrichment than open-ended entity
     discovery.

3. **SEC EDGAR public APIs**
   - Resolve and validate US public companies.
   - Track recent submissions and use filings as high-quality candidate
     evidence.
   - The SEC APIs require no key and are updated throughout the day. Automated
     access must follow SEC fair-access guidance.

4. **Nasdaq Trader symbol directory**
   - Maintain an exchange-symbol mapping and identify listing additions,
     deletes, and symbol changes.
   - Nasdaq states that symbol-directory files are updated periodically during
     the day.

### Tier 2: optional attention enrichment

5. **YouTube Data API**
   - Search for company and sector phrases using a configured API key.
   - Use it for a limited daily shortlist, not a scan of every security.
   - A `search.list` call costs 100 quota units and the default allocation is
     10,000 units per day. That implies roughly 100 one-page searches daily
     before other calls.

6. **Company investor-relations RSS feeds and press-release pages**
   - Add issuer-specific RSS or release feeds after a company reaches the
     tracked universe.
   - This improves catalyst quality but is not a universal discovery source.

### Social-media limitations

Do not make X, Instagram, TikTok, or Reddit post counts a required input until
their API terms, access model, and reproducibility are evaluated explicitly.
Broad social-media historical discovery is not currently a dependable free
foundation for this project. Treat any manually collected social observations
as optional evidence with a source timestamp.

## Candidate Discovery Pipeline

Run this as a recommendation workflow before allowing automatic additions.

### Step 1: create sector query packs

Each sector receives:

- exact phrases
- OR keyword groups
- exclusion words
- known-company aliases
- sector-specific catalyst phrases

Example:

```text
("liquid cooling" OR "data center cooling" OR "AI data center power")
AND (capacity OR backlog OR contract OR guidance OR partnership)
```

### Step 2: fetch recent public-news candidates

For each query pack:

- fetch the latest GDELT articles
- deduplicate by canonical URL
- extract company names and ticker-like tokens
- retain source domain, headline, URL, and publication timestamp
- count daily and seven-day mentions

### Step 3: resolve entities

Match extracted names against:

- existing `entities.csv` aliases
- SEC company tickers
- Nasdaq Trader symbol directory
- a manual alias override file for ADRs, OTC securities, and Canadian names

Do not auto-resolve ambiguous short ticker strings such as `AI`, `ON`, or `T`.
Require a company-name match or manual review.

### Step 4: enrich resolved candidates

For a resolved ticker:

- fetch Alpaca structured news
- optionally fetch YouTube search results if the candidate is shortlisted
- fetch available EOD price and volume history
- calculate current signal indicators
- record whether the ticker is already tracked or belongs to a related sector

### Step 5: rank candidates

Use a transparent score. Start simple and tune only after collecting forward
snapshots.

| Factor | Initial weight | Notes |
| --- | ---: | --- |
| Seven-day news acceleration | `20` | Reward mention growth versus the prior seven days |
| Source diversity | `15` | Reward coverage across distinct domains |
| Catalyst specificity | `15` | Contract, guidance, product launch, capacity, filing, or partnership |
| Sector relevance | `15` | Reward explicit match to a tracked bottleneck query pack |
| Price-volume setup | `15` | Reward a fresh or near technical signal without a large completed spike |
| SEC or issuer-primary evidence | `10` | Reward filing or investor-relations confirmation |
| Previously unseen but resolvable entity | `5` | Encourages expansion without overpowering evidence quality |
| Optional YouTube acceleration | `5` | Shortlist-only attention signal |

Apply penalties:

| Penalty | Initial value |
| --- | ---: |
| Already rose more than the configured pre-spike ceiling | `-20` |
| Only one low-quality source | `-15` |
| Ambiguous entity resolution | `-30` and require review |
| Unsupported symbol, stale listing, or missing EOD bars | `-100` |

Do not optimize weights against the same period used to judge performance.
Collect forward snapshots first, then compare versions out of sample.

## Promotion Rules

Use a staged model:

| State | Meaning |
| --- | --- |
| `candidate` | Discovered but unresolved or weakly supported |
| `monitor` | Resolved and tracked in the candidate queue |
| `review` | Meets a recommendation threshold |
| `approved` | Human-approved addition to the overall tracked universe |
| `sector-member` | Human-approved membership in one or more lists |

Initial recommendation:

- automatically create or refresh candidate rows
- automatically promote resolved candidates to `monitor`
- recommend `review` after a score threshold and at least two independent
  evidence URLs
- require human approval before adding to the overall tracked universe
- require human approval before adding to a simulated research portfolio

After the workflow has produced several weeks of auditable forward snapshots,
consider a controlled mode that automatically adds high-confidence candidates
to the **overall tracked universe only**. Do not automatically buy them.

## Removal Rules

Prefer archival over deletion. Historical rows must remain queryable.

Recommend removal from active scanning only when one of these conditions is
met:

- delisted, acquired, or symbol changed
- unsupported price history for a sustained period
- entity resolution was wrong
- manual removal
- no longer relevant to any tracked sector and no meaningful news, signal, or
  portfolio membership for a long review window such as 180 days

Use separate actions for:

- removing a ticker from one theme list
- removing a ticker from active overall scanning
- archiving a security after delisting or acquisition

Never use a weak signal as a reason to remove a ticker. Weak signals already
prevent variable portfolios from entering positions.

## Backtesting and Timing Rules

Universe expansion must follow the same EOD discipline as variable trades:

1. News, mentions, filings, and technical indicators are observed only after a
   completed close.
2. A deterministic or approved universe addition becomes eligible no earlier
   than the next available market session.
3. A variable-portfolio trade still executes at the next available ticker
   close after its signal is observable.
4. Historical backtests use the universe snapshot that existed on each date,
   not today's expanded list.

This avoids survivorship bias and look-ahead bias.

## Proposed Dashboard Views

Add these later:

- **Universe timeline**: overall additions, removals, restores, and archives
- **Ticker history**: lists joined and left over time, with evidence links
- **Sector timeline**: membership count and new candidates by sector
- **Candidate queue**: score, score components, first seen, latest evidence,
  current signals, and review action
- **Discovery source health**: API configuration, last successful refresh,
  throttling status, and daily usage
- **Coverage gaps**: sectors with few tracked entities or stale news

## Implementation Phases

### Phase 1: auditable manual approval

- create entity and membership-event files
- import the current tracked universe as initial events
- add a manual candidate-approval command
- render history and the candidate queue in the dashboard

### Phase 2: free-source discovery

- add GDELT sector query packs
- resolve names against SEC and Nasdaq datasets
- enrich shortlisted tickers with Alpaca news, EOD bars, and current signals
- write daily candidate snapshots

### Phase 3: optional attention signals

- configure a daily YouTube shortlist budget
- add issuer RSS feeds
- evaluate each additional social source separately before using it

### Phase 4: forward evaluation

- compare proposed additions with rejected and untouched candidates
- track signal quality after first discovery
- revise scoring thresholds using forward periods only
- optionally auto-add only high-confidence candidates to the tracked universe

## Primary References

- [Alpaca historical news data](https://docs.alpaca.markets/us/docs/historical-news-data)
- [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
- [GDELT DOC API extended search horizon](https://blog.gdeltproject.org/doc-geo-2-0-api-updates-full-year-searching-and-more/)
- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC developer resources and fair-access guidance](https://www.sec.gov/about/developer-resources)
- [SEC company tickers file](https://www.sec.gov/file/company-tickers)
- [Nasdaq Trader symbol-directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs)
- [YouTube Data API overview](https://developers.google.com/youtube/v3/getting-started)
- [YouTube `search.list` reference](https://developers.google.com/youtube/v3/docs/search/list)

