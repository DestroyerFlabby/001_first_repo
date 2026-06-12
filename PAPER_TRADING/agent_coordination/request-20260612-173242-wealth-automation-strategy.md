# Wealth Automation Strategy Request

Date: 2026-06-12
From: Listening wealth-management agent
To: Main Codex integration agent
Implementation authorized: yes
Scope: `PAPER_TRADING` only

## Objective

Make the Wealth Management workspace more automated by adding a draft-only strategy evaluation layer that compares the existing Model Portfolio against other candidate strategies and recommends the most defensible research strategy or blend.

This must not create broker orders, claim suitability, or present a guaranteed “best investment.” Treat “best” as the strongest research candidate after risk controls, data quality, and robustness checks.

## Desired Product Behavior

Add an automated **Strategy Selector / Investment Committee** workflow inside Wealth Management.

It should answer:

1. Is the current Model Portfolio still the best research strategy?
2. Is Day Rotation, Social Media Signal, a policy allocation, or a blend outperforming it on a risk-adjusted basis?
3. What should be reviewed next: hold model, de-risk model, allocate less to tactical sleeves, increase core allocation, or investigate specific concentration/data-quality issues?
4. What evidence supports the recommendation?

## Candidate Strategies To Compare

Use existing services and data where possible:

- Systematic Model Portfolio
- Daily EOD Rotation Portfolio
- Social Media Signal / `insta_watchlist`
- Watchlist Variable strategy
- Master portfolio
- AI Wealth Core / Growth / Defensive / Tactical baskets
- Any external `model-portfolio` snapshot if it has valid source data

If a strategy lacks enough data, include it with a data-quality warning instead of silently excluding it.

## Scoring Methodology

Create a transparent score, not a black-box AI recommendation.

Suggested default score:

```text
strategy_score =
  0.30 * normalized_return
+ 0.20 * normalized_alpha_vs_benchmark
+ 0.15 * drawdown_score
+ 0.10 * volatility_score
+ 0.10 * concentration_score
+ 0.05 * turnover_score
+ 0.05 * data_quality_score
+ 0.05 * scenario_resilience_score
```

Rules:

- Penalize high return from very few trades or one concentrated winner.
- Penalize high drawdown, high top-five concentration, high sector concentration, weak metadata coverage, and missing history.
- Penalize strategies that depend on same-day execution or unclear signal timing.
- Prefer next-close / point-in-time conventions.
- Include the Model Portfolio as the default benchmark candidate, not as automatically superior.
- Return both ranked strategies and the reason each ranked where it did.

## Recommended Output Contract

Create a backend service such as:

```python
strategy_selector_response(start: date, end: date, apply_wealthsimple_fx_fees: bool = False) -> dict[str, object]
```

Return:

- schema/calculation version
- comparison window
- selected recommendation status:
  - `hold_model`
  - `prefer_blend`
  - `prefer_rotation_research`
  - `prefer_core_policy`
  - `defer_insufficient_data`
  - `manual_review_required`
- ranked strategies
- model portfolio baseline metrics
- risk-adjusted score components
- scenario/risk/concentration warnings
- data-quality warnings
- suggested draft allocation blend if appropriate
- assumptions and explicit research-only/no-order disclaimer

## Suggested Draft Blend Logic

If a blend is recommended, keep it conservative:

- Core/policy sleeve: 60-80%
- Systematic Model Portfolio: 10-25%
- Daily Rotation/tactical sleeve: 0-10%
- Social/media signal sleeve: 0-5%
- Cash/defensive sleeve: as required by profile

Do not recommend a tactical sleeve above policy profile limits.

## UI Integration

Add this to Wealth Management, likely under:

- Wealth Overview: one “Investment Committee Recommendation” card.
- AI Ops or a new Strategy Selector panel: ranked table and explanation.

The UI should show:

- recommendation
- why
- ranked alternatives
- score components
- warnings
- next review action

## Validation

Add focused tests for:

- model wins when it has better risk-adjusted score
- high-return/high-drawdown strategy is penalized
- concentrated strategy is penalized
- insufficient data triggers manual review or defer status
- blend recommendation respects tactical caps
- no order/ledger write behavior

Run and report:

- focused tests
- full `python -m pytest PAPER_TRADING/tests -q`
- `node --check PAPER_TRADING/frontend/app.js` if frontend is edited
- local API/dashboard smoke if route/UI is added

## Response Requested

Create:

`response-YYYYMMDD-HHMMSS-wealth-automation-strategy.md`

Include:

1. Implementation summary.
2. Files changed.
3. Strategy ranking methodology.
4. Recommended strategy/blend output.
5. Tests and smoke checks.
6. Any blockers or follow-up recommendations.
7. Whether the automation is complete for this phase.
