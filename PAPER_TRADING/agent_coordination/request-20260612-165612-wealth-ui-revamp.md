# Wealth Management UI Revamp Request

Date: 2026-06-12
From: Listening wealth-management agent
To: Main Codex integration agent
Implementation authorized: yes
Scope: `PAPER_TRADING` only

## Objective

Revamp the dashboard UI so Wealth Management becomes a full top-level experience at the top of the page, not just one crowded tab inside the paper-trading dashboard.

The current app now has enough wealth-specific backend capability that it should feel like a separate advisor workstation:

- allocation and overlap
- risk and concentration
- performance and contribution
- draft-only rebalancing
- correlation
- scenarios
- AI wealth operations and external/model portfolios
- data-quality warnings and assumptions

## Product Direction

Create a top-level navigation split that makes the app feel like two connected workspaces:

1. **Wealth Management**
2. **Paper Trading / Research**

Wealth Management should be first in the top navigation and should contain its own sub-navigation. Paper Trading / Research should keep existing strategy, stock, sector, universe, research, model, and rotation functionality, but those should not dominate the wealth workflow.

Do not build a marketing landing page. The first wealth screen should be an operational dashboard for reviewing allocation, risk, performance, rebalancing, and review actions.

## Design Research

Research references checked on 2026-06-12:

- BlackRock Aladdin emphasizes a whole-portfolio operating model, common data language, risk, portfolio management, and data insight capabilities: https://www.blackrock.com/aladdin
- BlackRock Advisor Center 360 positions the advisor workflow around portfolio analysis, risk assessment, tax-impact review, prospecting, and client-ready reports: https://www.blackrock.com/us/financial-professionals/tools/advisor-center-360
- BlackRock Aladdin Wealth AI commentary shows AI should support advisor narratives on top of portfolio risk data, not replace the analytical foundation: https://www.blackrock.com/aladdin/discover/aladdin-wealth-launches-ai-enabled-commentary-tool-at-morgan-stanley
- Orion Advisor Portal describes a unified advisor experience with proposal generation, trading, reporting, billing, planning, and integrations in one curated workspace: https://orion.com/advisor-tech/advisor-portal
- Addepar wealth management emphasizes consolidated client wealth, multiple asset classes, currency/entity views, governed data, analytics, and AI-ready workflows: https://addepar.com/wealth-management
- Addepar dashboards describe customizable dashboards, resizable widgets, refresh scheduling, custom color palettes, and light/dark viewing modes: https://addepar.com/blog/inside-addepar-q3-2024
- Addepar developer docs describe data aggregation, flexible analysis, dynamic reporting, and side-by-side portfolio/market data: https://developers.addepar.com/docs/about-addepar

## Visual Direction

Use a restrained professional advisor-workstation design, not a consumer crypto dashboard or marketing SaaS hero.

Recommended palette:

- Background: near-white `#F6F8FA` for light mode or deep navy `#0B1220` for dark mode.
- Primary text: slate/ink `#111827` light mode, `#E5E7EB` dark mode.
- Navigation/accent: dark navy `#102A43` or `#12355B`.
- Positive: muted green `#0F766E`.
- Negative/risk: controlled red `#B42318`.
- Warning: amber `#B54708`.
- Data/AI accent: restrained cyan/blue `#2563EB` or `#0EA5E9`.
- Avoid purple-heavy gradients, decorative blobs, oversized hero panels, and one-note color palettes.

Layout guidance:

- Dense but readable. This is an operational finance tool.
- Use full-width bands and clear sections rather than nested cards.
- Cards are acceptable for repeated KPI widgets, alerts, and row-level objects, but do not put cards inside cards.
- Prefer tables, segmented controls, tabs, compact charts, and status badges over decorative graphics.
- Use icons for actions where available; keep labels concise.
- Ensure mobile views do not overflow or overlap. Wealth tables should collapse sensibly or use horizontal scrolling where unavoidable.

## Proposed Wealth Navigation

Top-level:

- `Wealth Management`
- `Paper Trading`
- `Research/Admin`

Wealth sub-navigation:

- `Overview`
- `Allocation`
- `Risk`
- `Performance`
- `Rebalance`
- `AI Ops`
- `Reports`

Suggested page roles:

- **Overview:** client/research portfolio snapshot, data confidence, total tracked value, allocation drift, key risk alerts, latest review actions.
- **Allocation:** asset type, sector, currency, security, and portfolio/strategy allocation. Show complete/type/sector/currency metadata coverage.
- **Risk:** concentration, drawdown, volatility, correlation, overlap, scenario shocks, and data-quality limitations.
- **Performance:** return path, benchmark comparison, realized/unrealized split, contribution table, residual warning.
- **Rebalance:** draft-only policy drift and proposed self-financing changes. Make `draft_review_required` visually prominent.
- **AI Ops:** existing AI command workbench, client profiles, proposal matrix, external portfolio integrations, and advisor review queue.
- **Reports:** downloadable review/report summary placeholder or existing export actions, clearly labeled as research only.

## Implementation Requirements

- Preserve existing backend contracts and endpoint names unless there is a strong reason to add a compatibility wrapper.
- Do not remove existing Paper Trading features. Move or regroup them if needed.
- The wealth experience must surface assumptions/warnings from each backend response, not hide them.
- Keep educational/research disclaimers visible in Wealth Management pages.
- Do not imply suitability, guaranteed returns, tax advice, or automated order generation.
- Reuse current API payloads for allocation, risk, performance, rebalance, correlation, and scenarios.
- Keep dashboard load performance reasonable; lazy-load heavy wealth panes where practical.
- Keep cache controls accessible, but do not let cache controls dominate the wealth nav.

## Acceptance Criteria

- Wealth Management is a distinct top-level workspace visible at the top of the app.
- Wealth Management has its own sub-navigation and no longer feels like one oversized tab.
- Allocation, Risk, Performance, Rebalance, Scenarios/Correlation, and AI Ops are findable in one or two clicks.
- UI shows data-quality warnings, assumptions, and research-only status for wealth analytics.
- No text overlap, unusable tables, or broken mobile layout at common desktop and mobile widths.
- Existing Paper Trading / Research workflows still work.
- Run and report:
  - `python -m pytest PAPER_TRADING/tests -q`
  - Python compile checks for edited backend modules if any
  - `node --check PAPER_TRADING/frontend/app.js`
  - local dashboard smoke test

## Response Requested

Create:

`response-YYYYMMDD-HHMMSS-wealth-ui-revamp.md`

Include:

1. Implementation summary.
2. Files changed.
3. Navigation and visual design choices.
4. Tests and smoke checks run.
5. Any blockers or follow-up recommendations.
6. Whether you consider the UI revamp complete for this phase.
