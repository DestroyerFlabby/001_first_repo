# Wealth Management Dashboard And Portfolio Weighting Plan

Date: 2026-06-12
Agent: Codex wealth-management planning
Scope: `PAPER_TRADING` research and planning only

## 1. Executive Recommendation

Reorganize the product around four decisions rather than adding more isolated statistics:

1. **What do I own?** Household allocation, account structure, currency, strategy, and look-through exposure.
2. **What risks dominate?** Concentration, drawdown, volatility, correlation, liquidity, and data confidence.
3. **Why did performance differ?** Contributions, attribution, cash flows, fees, FX, and benchmark-relative results.
4. **What action is justified?** Policy-aware rebalancing proposals with trade thresholds, costs, confidence, and human review.

The default construction method should be **policy allocation plus constrained risk-adjusted weights**, not unconstrained mean-variance optimization and not direct AI/news score weighting. Strategic asset allocation should determine at least 80-90% of risk-policy exposure. Tactical and signal-driven sleeves should remain bounded, transparent, and subordinate to name, sector, currency, liquidity, volatility, turnover, and drawdown controls.

Recommended default security weight inside an approved sleeve:

```text
base_i = 1 / max(trailing_volatility_i, volatility_floor)
tilt_i = clamp(1 + tactical_strength * standardized_score_i, 0.75, 1.25)
raw_i  = base_i * tilt_i * liquidity_multiplier_i * confidence_multiplier_i
weight = constrained_normalize(raw, name_caps, sector_caps, currency_caps, cash_target)
```

This uses inverse volatility as a stable starting point, allows only a modest score tilt, and applies hard constraints after scoring. AI output should explain or prioritize review; it should not bypass portfolio policy.

## 2. Current-State Assessment

### Reusable capabilities

- `backend/dashboard_service.py` already produces portfolio value series, holdings, realized positions, trade ledgers, benchmark comparisons, sector exposure, and optional Wealthsimple FX-fee estimates.
- `backend/model_portfolio_service.py` already implements point-in-time model selection, score and volatility inputs, next-close-style execution, position/sector caps, cash, rebalance bands, turnover, drawdown, realized P/L, and benchmark comparison.
- `backend/day_rotation_service.py` provides a separate higher-turnover EOD strategy with explicit caps and rebalance bands.
- `backend/dashboard_cache.py` and background overview jobs provide an established cache/job pattern suitable for heavier analytics.
- `backend/universe_service.py` and `data/asset_universe.csv` contain asset type, currency, sector, exchange, and benchmark eligibility.
- `backend/benchmark_service.py`, `data/benchmark_registry.csv`, baskets, strategy registry, and external portfolio registry provide reusable policy metadata.
- Wealth modules already contain client policy profiles, proposed model allocations, policy warnings, AI review commands, and research-only guardrails.
- The frontend already supports date windows, sortable tables, drilldowns, Excel export, mobile layouts, model/rotation pages, research, and data-quality messaging.

### Material limitations

- Current paper-ledger reporting explicitly excludes deposits, withdrawals, dividends, fees, interest, and FX cash movements. Household-level return, contribution, income, and tax analysis would therefore be incomplete or misleading.
- There is no canonical account/household schema connecting owner, account type, registration type, tax jurisdiction, base currency, objective, liability, and liquidity need.
- Geography, issuer domicile, ETF look-through holdings, duration, credit quality, yield, tax lot, adjusted cost base, and dividend entitlement are not consistently available.
- Existing benchmark comparison is useful but does not yet provide allocation/selection attribution, tracking error, information ratio, downside deviation, or recovery statistics.
- Model and rotation portfolios have separate portfolio engines. Shared risk, constraint, and reporting calculations should be extracted before introducing more optimizers.
- Yahoo-derived close data and ad hoc news data are appropriate for research, but every page must expose freshness, missing-history, source, and calculation confidence.

### Navigation issue

The current top-level navigation mixes operational tools, research, portfolio views, and wealth workflows. Keep existing functionality but group it by user task. Avoid placing household wealth, model research, and universe administration at the same hierarchy level.

## 3. Proposed Page And Navigation Structure

### A. Overview

Replace the generic home summary with a **Total Wealth Overview** when household data exists; retain a research-portfolio overview otherwise.

- Net investable assets, allocation versus policy, cash, currency exposure, top concentration, trailing return, maximum drawdown, and data confidence.
- Account and strategy contribution waterfall.
- Alerts limited to decisions: policy breach, stale price, excessive concentration, drawdown threshold, cash shortfall, or rebalance candidate.
- Decision supported: determine whether allocation, risk, or data requires attention before reviewing individual securities.

### B. Allocation

One page with tabs for asset class, geography, currency, sector, account, and strategy. Show current, target, drift, proposed, and policy range. Add ETF look-through only when source data is reliable.

- Decision supported: identify unintended bets and choose which sleeve should fund a rebalance.
- Reuse: holdings, sectors, currency, client profiles, model allocations.
- Missing data: asset-class taxonomy, geography, account identifiers, ETF constituents.

### C. Risk

Combine existing drawdown views with:

- Annualized volatility, downside deviation, maximum drawdown, current drawdown, recovery duration, rolling beta, tracking error, and marginal contribution to risk.
- Concentration by position/sector/currency plus effective number of holdings, `1 / sum(w_i^2)`.
- Correlation heatmap and clustered overlap, with both direct ticker overlap and ETF look-through overlap when available.
- Historical scenarios such as 2020 shock, 2022 stock/bond decline, rate shock, CAD move, technology drawdown, and crypto drawdown. Clearly label historical replay versus hypothetical shock.
- Decision supported: reduce dominant risk, distinguish true diversification from a high holding count, and evaluate whether a proposal fits its intended risk profile.

### D. Performance And Attribution

- Time-weighted return for manager/strategy evaluation and money-weighted return for household experience once cash flows are complete.
- Gross and net results, benchmark for every displayed period, FX contribution, fees, income, realized/unrealized P/L, and allocation/selection attribution where valid.
- Drawdown and recovery table beside cumulative performance, not on a separate decorative page.
- Decision supported: determine whether results came from market exposure, active decisions, currency, concentration, or cash-flow timing.

### E. Rebalancing

- Current versus policy target, minimum/maximum bands, proposed trades, estimated turnover, estimated costs, tax-lot warning, cash impact, and reasons.
- Require a staged state: `draft -> reviewed -> approved -> exported`; never create broker orders automatically.
- Decision supported: execute the smallest policy-restoring trade set rather than trading to exact targets unnecessarily.

### F. Goals And Cash Flow

- Goal amount/date, current funded ratio, required real return, projected range, contribution requirement, liquidity reserve, and sequence-risk warning.
- Do not implement probability-of-success claims until assumptions, inflation, cash flows, taxes, and simulation methodology are documented.
- Decision supported: adjust savings, horizon, spending, or risk rather than treating return maximization as the only lever.

### G. Client Review

- Date-stamped downloadable review: objectives, policy allocation, changes, performance versus benchmark, material risks, fees/cost assumptions, data limitations, and approved action list.
- AI may draft commentary only from computed facts and must cite metric dates and sources.
- Decision supported: create an auditable, consistent review record.

### H. Research And Administration

Move Universe, Strategy Lab, raw Signals, News, Baskets, and data registries under **Research/Admin**. Model Portfolio and Day Rotation remain research strategies, linked from Performance and Risk rather than competing with household navigation.

## 4. Proposed Portfolio-Weighting Methodology

### Policy hierarchy

1. Define base currency, objective, horizon, liquidity need, risk capacity, risk tolerance, constraints, benchmark, and allowed assets.
2. Select a strategic allocation with explicit policy ranges.
3. Reserve cash before risky-asset sizing.
4. Allocate each sleeve using a robust method appropriate to its purpose.
5. Apply security and aggregate constraints.
6. Generate trades only when drift exceeds tolerance and expected benefit exceeds cost.
7. Subject all proposals to data-quality and human-review gates.

### Strategic versus tactical

- Strategic allocation: normally 80-90% or more of policy exposure; reviewed annually or after a material client change.
- Tactical allocation: default cap 10%, aggressive research profile maximum 20%; reviewed monthly, not changed solely because of one news item.
- Social/news/model confidence modifies weights by a bounded multiplier, recommended range 0.75-1.25. It cannot increase a position above policy caps or eliminate required cash/fixed-income allocations.

### Method comparison

| Method | Appropriate use | Main weakness | Recommendation |
|---|---|---|---|
| Equal weight | Small, homogeneous stock sleeve | Ignores volatility and liquidity | Baseline and fallback |
| Market-cap weight | Broad passive equity beta | Concentrates in largest issuers and embeds market composition | Default for low-cost core ETFs |
| Inverse volatility | Heterogeneous liquid securities | Ignores correlations and can crowd low-volatility assets | Default active-sleeve base weight |
| Risk parity | Multi-asset sleeves with reliable covariance | Estimation, leverage, duration concentration | Research alternative; no leverage initially |
| Minimum variance | Large liquid universe with robust covariance | Highly sensitive to estimates and constraints | Optional constrained comparison only |
| Maximum diversification | Diversification-focused equity/multi-asset research | Similar covariance instability | Optional research benchmark |
| Score weighted | Tactical/model sleeve | Can concentrate and overfit | Use only as bounded tilt on risk weights |

### Default constraints

Initial educational defaults, configurable by profile and subject to validation:

- Core individual stock: 5% target maximum, 7% hard maximum.
- Tactical individual stock: 3% target maximum, 5% hard maximum.
- Broad diversified ETF: up to 40% where it represents a strategic sleeve.
- Narrow sector/thematic ETF: 10% target maximum, 15% hard maximum.
- Sector: 25% active-sleeve maximum or benchmark weight plus 10 percentage points, whichever policy selects.
- Single theme across stocks and ETFs: 15-20% depending on profile.
- Crypto: 0% conservative, 2% balanced, 5% growth, 10% research/aggressive maximum; no assumption that all crypto positions diversify each other.
- Unhedged foreign currency: report gross exposure; apply policy cap by household base currency and distinguish security risk from FX risk.
- Minimum cash: 5% model default, increased for near-term withdrawals; current model engines already target 95% invested.
- Liquidity: position must be small relative to trailing median dollar volume; reject or haircut weights when history or volume is unavailable.

### Rebalancing

- Strategic sleeves: monthly monitoring, quarterly scheduled review, annual policy review.
- Tactical model: weekly or monthly depending on signal horizon; the existing daily rotation remains a separate research strategy.
- Trade when `abs(current_weight - target_weight) > max(absolute_band, relative_band * target_weight)`.
- Suggested starting bands: 2 percentage points absolute for strategic sleeves, 20% of target relative, and existing model-specific bands where already tested.
- Add a no-trade rule when estimated benefit is below spread, commissions, FX cost, tax impact, and minimum trade size.
- Use partial rebalancing toward the nearest acceptable policy boundary before exact-target trading.

### Drawdown control

- Do not liquidate solely because a trailing drawdown exists; that can institutionalize selling after losses.
- Use staged controls tied to both portfolio drawdown and evidence of risk change:
  - Warning at 8%: review data, concentration, volatility, and thesis.
  - Tactical risk reduction at 12% if volatility or correlation also breaches policy.
  - Governance review at 15% or strategy-specific historical limit.
- De-risk tactical sleeves first; strategic policy changes require documented client/policy review.

### Benchmarks

- Household: policy-weighted blended benchmark with weights fixed or changed only when policy changes.
- Broad equity sleeve: investable total-return index matching geography and currency treatment.
- Model stock sleeve: broad equity benchmark plus a secondary equal-weight universe benchmark.
- Tactical/rotation: benchmark plus cash, with identical start/end dates and next-close execution.
- Crypto: separate crypto benchmark; do not compare a crypto sleeve only with SPY.
- Always show benchmark methodology, currency, total-return/price-return status, and rebalance schedule.

### Backtest requirements

- Store every signal, universe membership, classification, price, FX rate, and model version with an `as_of` timestamp.
- Select using information available at close on day `t`; execute at next available close on `t+1` unless a different executable convention is explicitly modeled.
- Use delisted and historical constituents where possible; never reconstruct an old universe from today’s surviving tickers.
- Walk-forward parameter selection; freeze parameters before out-of-sample evaluation.
- Include spread/slippage, FX, fees, turnover, cash drag, failed data, and stale-price behavior.
- Report sensitivity across nearby parameters and multiple regimes. Reject a method whose result depends on one narrow parameter setting.

## 5. Research Findings And Sources

Accessed 2026-06-12. Sourced facts are separated from recommendations above.

- CFA Institute describes portfolio construction around asset allocation, diversification, benchmarking, and investment risk: https://rpc.cfainstitute.org/topics/portfolio-construction-and-investment
- CFA Institute risk-profiling research integrates goals, assets, savings, willingness, and ability to assume risk rather than relying on one questionnaire score: https://rpc.cfainstitute.org/sites/default/files/-/media/documents/survey/investment-risk-profiling.pdf
- CFA Institute backtesting guidance recommends rolling/walk-forward testing and explicitly warns about survivorship and look-ahead bias: https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/backtesting-and-simulation
- CFA Institute model-validation research discusses look-ahead and survivorship bias in investment models: https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/investment-model-validation.pdf
- MSCI explains that minimum-volatility indexes minimize estimated risk within constraints intended to retain investability and replicability: https://www.msci.com/indexes/group/minimum-volatility-indexes
- S&P Risk Parity methodology targets equal risk across equity, fixed income, and commodity components: https://www.spglobal.com/spdji/en/documents/methodologies/methodology-sp-risk-parity-indices.pdf
- AQR’s risk-parity research emphasizes diversification by risk while noting that risk parity does not outperform in every environment: https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Understanding-Risk-Parity.pdf
- AQR’s implementation research emphasizes trading toward theoretical weights only when expected benefit justifies real-world costs: https://www.aqr.com/-/media/AQR/Documents/Insights/Working-Papers/AQR--Craftsmanship-Alpha.pdf
- GIPS benchmark guidance calls for benchmark returns for the same periods as reported portfolio returns when an appropriate benchmark exists: https://www.gipsstandards.org/wp-content/uploads/2023/08/gs_benchmarks_firms.pdf
- GIPS calculation guidance explains time-weighted return as a way to remove the effect of external client cash flows when assessing management performance: https://www.gipsstandards.org/wp-content/uploads/2021/03/calculation_methodology_gs_2011.pdf
- CIRO KYC/suitability guidance says suitability is not one-size-fits-all and supports a risk-based process: https://www.ciro.ca/newsroom/publications/know-your-client-and-suitability-determination-retail-clients
- The 2025 CSA/CIRO review reinforces KYC, KYP, and suitability practices under Canadian client-focused reforms: https://www.securities-administrators.ca/wp-content/uploads/2025/12/csa-ciro_20251210_31-368_client-focused-reforms_ENG.pdf
- CSA research describes CRM2’s purpose as improving cost and performance transparency: https://www.securities-administrators.ca/wp-content/uploads/2024/04/CRM2-Executive-Summary.pdf
- Bank of Canada Valet provides official exchange-rate/economic data and recommends caching daily data: https://www.bankofcanada.ca/valet-api-how-to/
- SEC enforcement against misleading AI claims demonstrates the need to substantiate any claim about AI use: https://www.sec.gov/newsroom/press-releases/2024-36

Professional convention: constrained optimization, policy ranges, total-return benchmarks, explicit cost assumptions, and separate TWR/MWR serve different reporting purposes. Recommendation: apply these conventions conservatively in an educational product and obtain Canadian legal/compliance review before presenting suitability, tax, or regulated-advice workflows to clients.

## 6. Data And Architecture Requirements

### Proposed domain records

- `households`: base currency, jurisdiction, review date.
- `accounts`: household, account type, registration type, owner, tax treatment, custodian.
- `cash_flows`: deposit, withdrawal, dividend, interest, fee, tax, FX transfer with effective date.
- `tax_lots`: quantity, acquisition date, adjusted cost base, currency, source confidence.
- `goals`: amount, date, priority, inflation assumption, recurring contribution/withdrawal.
- `policy_allocations`: target/min/max by asset class, currency, sector/theme, and strategy.
- `instrument_metadata_history`: point-in-time sector, geography, currency, asset class, liquidity, ETF look-through version.
- `portfolio_snapshots`: holdings, weights, prices, FX rates, model version, calculation version, and data-quality state.

CSV can remain an import format, but household and historical snapshot data should move to SQLite/PostgreSQL before multi-user or auditable use. Append-only history is important; current-state CSV replacement is insufficient for point-in-time reconstruction.

### Services and contracts

- Extract shared `performance_service`, `risk_service`, `allocation_service`, `attribution_service`, `policy_service`, and `rebalance_service` rather than expanding `dashboard_service.py` further.
- Version endpoints, or include `schema_version`, `calculation_version`, `as_of`, `base_currency`, `data_quality`, and `assumptions` in every analytics response.
- Likely future endpoints: `/api/wealth/overview`, `/allocation`, `/risk`, `/performance`, `/rebalance`, `/goals`, and `/review-report`.
- Reuse the existing background-job pattern for covariance, correlation, scenario matrices, attribution, optimization, and report generation.
- Cache by household/portfolio, as-of date, base currency, benchmark, methodology version, and fee/tax setting. Invalidate only affected snapshots.

### Render and mobile performance

- Do not calculate a full covariance matrix or replay every strategy on each page load. Run nightly or on-demand jobs and serve immutable snapshots.
- Limit correlation matrices on mobile to top exposures or clusters; provide full export separately.
- Return chart-ready aggregates rather than raw daily holdings history.
- Lazy-load page modules after navigation instead of expanding the initial `Promise.all` payload.
- Use server-generated reports; browser-side Excel/PDF assembly will become expensive and inconsistent.

### External dependency review

`PERSONAL_WEALTH_PLANNING` may contain goals, liabilities, or planning assumptions, but this phase must not read or edit it implicitly. Define an explicit, versioned import contract later. No cross-folder runtime dependency should be introduced until ownership, privacy, and update behavior are agreed.

## 7. Phased Implementation Plan

### Phase 1: Immediate improvements using existing data

| Item | Value | Backend/frontend | Tests | Performance/risks | Priority/complexity |
|---|---|---|---|---|---|
| Allocation and concentration page | Exposes current sector, currency, asset-type, strategy, and name risk | Aggregate existing holdings; add current/target/drift tables and filters | Weight totals, duplicate holdings, unknown metadata, responsive tables | Cache daily; classifications may be incomplete | P0 / Medium |
| Unified risk summary | Makes volatility, drawdown, recovery, concentration, and benchmark risk comparable | Shared calculations over existing series; compact Risk page | Known synthetic series, missing dates, zero variance, benchmark alignment | Daily cached series; disclose short histories | P0 / Medium |
| Data-quality framework | Prevents false precision | Standard response envelope and visible freshness/confidence states | Stale, missing, conflicting, and partial source fixtures | Low cost; requires consistent adoption | P0 / Small-Medium |
| Rebalance drift preview | Converts profile allocations into bounded review actions | Policy ranges and draft-only proposal API/UI | Caps, bands, cash, weight conservation, no-order guarantee | Low compute; incomplete tax/cost data must be explicit | P0 / Medium |
| Navigation reorganization | Reduces task switching and mobile overload | Group Wealth, Portfolios, Research/Admin; lazy-load modules | Navigation and mobile viewport tests | Lower initial load if implemented with lazy fetch | P1 / Medium |

### Phase 2: Medium-complexity analytics

| Item | Value | Required data and changes | Tests | Performance/risks | Priority/complexity |
|---|---|---|---|---|---|
| Contribution analysis | Shows securities and sleeves driving results | Daily position weights and returns; attribution service and waterfall | Contributions reconcile to return within tolerance | Cache by period; corporate actions can break reconciliation | P1 / Medium-High |
| Correlation and overlap | Reveals duplicated risk | Aligned return histories; optional ETF holdings | Pairwise missing data, symmetry, PSD warnings | Background calculation; top-N mobile view | P1 / Medium |
| Scenario testing | Quantifies exposure to defined shocks | Historical windows, factor/FX shocks, scenario registry | Reproducible shocks and sign conventions | Async; label hypothetical versus replay | P1 / Medium-High |
| Client review export | Creates dated, auditable summary | Existing analytics plus assumptions/disclosures | Snapshot consistency and export smoke tests | Server-side generation; compliance wording review | P1 / Medium |
| Bank of Canada FX integration | Improves CAD household reporting | Cached Valet daily rates and source metadata | Missing holidays, inversion, stale rates | Daily cache; indicative rates are not execution rates | P1 / Medium |

### Phase 3: Advanced construction and optimization

| Item | Value | Required changes | Tests | Performance/risks | Priority/complexity |
|---|---|---|---|---|---|
| Shared constrained weighting engine | Makes model methods comparable and governed | Constraint solver, covariance estimator, methodology registry | Feasibility, caps, deterministic results, degenerate covariance | Async; solver dependency and estimate instability | P2 / High |
| Walk-forward optimizer lab | Compares equal, cap, inverse-vol, risk parity, min-var, diversification, and bounded score tilt | Point-in-time universe and model-version snapshots | Look-ahead sentinels, next-close fills, costs, out-of-sample splits | Expensive; cache immutable runs | P2 / High |
| Marginal risk and risk budgeting | Sizes sleeves by portfolio risk rather than dollars alone | Stable covariance/factor model | Risk contributions sum to total risk | Sensitive to history/regime; confidence bands required | P2 / High |
| Goal projections | Connects portfolio policy to required return and savings | Complete goals, cash flows, inflation, liabilities | Deterministic seeds, boundary cases, assumption sensitivity | Async Monte Carlo; avoid false precision | P2 / High |

### Phase 4: Blocked by unavailable or unreliable data

- Tax-aware harvesting and location: blocked by verified adjusted cost base, tax lots, superficial-loss tracking, jurisdiction, and account registration data.
- Complete income/dividend reporting: blocked by authoritative distributions, withholding tax, reinvestment, and cash ledger reconciliation.
- Household money-weighted return: blocked by complete external cash flows.
- ETF look-through concentration: blocked by dated constituent/weight feeds and licensing/refresh rules.
- Fixed-income risk: blocked by duration, yield, maturity, credit, callable features, and accrued interest.
- Suitability determination or personalized recommendation: blocked by validated KYC/KYP workflow, registration/compliance review, audit controls, and human accountability.

## 8. Open Questions And Identified Conflicts

1. Is the intended unit a research portfolio, one person’s household, or a future multi-client adviser platform? The schema and privacy requirements differ materially.
2. What is the base reporting currency: CAD, USD, or selectable by household?
3. Should the systematic Model Portfolio replace the external `model-portfolio` placeholder, or should both remain distinct as internal and external strategies?
4. Are model profiles educational examples or intended future client policies? They must remain clearly labeled until a governed onboarding process exists.
5. Which benchmark licenses and total-return data sources are acceptable for production use?
6. Is PostgreSQL available on Render, or must the next phase remain file-backed?
7. No application files were modified for this assignment. Concurrent dashboard and wealth implementation changes remain untouched.
8. The combined working tree should not be committed solely on the basis of this plan; the separate coordination response already requires full merged tests, compilation, diff checks, and endpoint/browser smoke testing.
