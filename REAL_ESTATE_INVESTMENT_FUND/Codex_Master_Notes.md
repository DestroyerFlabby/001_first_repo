🏗️ Real Estate Fund Builder — Codex Master Notes
1. Purpose

This script and supporting Excel model simulate a $1.5 million equity-raised real-estate investment portfolio across Ontario (GTA, Kitchener, London, Kingston).
The goal: achieve a conservative 5-year IRR around 10%, below market “fund-of-funds” targets (12–15%), while remaining realistic and scalable.

2. Core Model Components

Files:

realestate_portfolio_model.py → Generates Excel.

RealEstate_Portfolio_5yr_Conservative.xlsx → Outputs 5-year projections.

RealEstate_Portfolio_5yr_Expanded.xlsx → Adds LP/GP waterfall & notes.

Key assumptions

Equity raise: 1.5M
LTV: 75%  (controls ~6M assets)
Amortization: 25 years
Rates: Low 4.3%, Mid 4.6% (used), High 5.5%
Vacancy: 5%
Maintenance: 8% of rent
Management: 8% of rent
Insurance: 0.20% of property value/yr
Rent growth: 2%
Price appreciation: 2.5%
Expense growth: 2%
Hold period: 5 years
Disposition cost: 1%
GP management fee: 1%/yr on equity
Preferred return: 8%
Carried interest: 20% promote

3. Property Archetypes
Strategy	Property Type	City Example	Role
Swing	2-bed Condo	GTA	Near-term CF-negative, long-term upside
Neutral	Townhome/Semi	Kitchener	Stable, near breakeven
CF-positive	Duplex	London	Cash-flow buffer, hedges risk
4. Portfolio Mix (Conservative)
City	Type	Count	Est. Total
London	Duplex (CF+)	6	$3.9 M
Kitchener	Townhome	2	$1.2 M
GTA	Condo	1	$0.7 M
Total			≈ $5.8 M Assets (~$1.5 M Equity)

Expected Outcomes (base case):

Gross IRR: ~10.2%

Cash-on-Cash: ~5.2%

Equity Multiple (5 yr): ~1.55×

5. LP/GP Waterfall Logic

Hurdle: 8% pref to LPs.
Step 1: 100% cash to LP until pref met.
Step 2: Return of capital (100% LP).
Step 3: GP catch-up to 20% of profits above pref.
Step 4: Split 80% LP / 20% GP thereafter.
Mgmt fee: 1% annual on equity (expensed).

The Excel LP_GP_Waterfall sheet computes:

LP Net IRR / Multiple

GP Promote and Fee income

Aggregate Fee Drag

6. Execution Order & Expert Team
Step 1 – Foundation

Legal Counsel (Real-Estate & Fund Law)

Draft LP/GP structure & subscription docs

Handle purchase contracts and due diligence

Do this first — all else depends on entity setup

Accountant / Tax Advisor

Model corporate vs LP taxation, CCA, passive-income rules

Coordinate with legal on structure

Step 2 – Capital & Financing

Investor Relations / Fund Admin

LP onboarding, reporting, audits

Mortgage Broker / Debt Advisor

Structure multi-property financing lines, negotiate covenants

Step 3 – Acquisition & Operations

Realtor / Acquisition Specialist

Source off-market deals, local comps

Property Manager (Regional Teams)

Leasing, maintenance, compliance

Integrate with underwriting models

Construction / Reno Partner

Duplex conversions, value-add projects

Step 4 – Growth & Governance

Auditor: Annual sign-off (LP trust).
Advisory Board: Provide oversight, attract follow-on capital.

7. Communication Strategy
Expert	Key Message
Lawyer	“Need fully compliant LP/GP structure, CRA-aligned, protect LP capital.”
Accountant	“Please test passive vs active tax outcomes and CCA optimization.”
Debt Advisor	“We plan $6M + deployment over 12–18 months; seeking flexible, multi-asset financing.”
Property Manager	“Looking for scalable systems, professional reporting.”
Contractor	“We’ll provide steady pipeline, transparent budgets.”
Fund Admin	“Quarterly LP reports, NAV, distribution tracking — fully transparent.”
8. Execution Timeline (6–12 Months)
Phase	Months	Key Deliverables
Setup	0–2	Legal + Tax structure, draft PPM
Capital	2–4	LP commitments, fund admin onboard
Financing	3–5	Debt lines arranged
Acquisition 1	4–6	First 2–3 properties closed
Stabilization	6–9	Rent-up & ops refinement
Reporting / Audit	9–12	Q4 report + audited statements
9. Strategic Positioning Notes

Market as “data-driven Ontario income-plus growth fund” targeting 10% conservative IRR with LP protection.

Emphasize professional structure (legal + audit) to differentiate from small syndicates.

Use the conservative model for LP presentations; keep optimistic case internal for upside demonstration.

10. Next Build Options

Add a Monte Carlo / Scenario tab (rates, rent, appreciation).

Create Gantt or slide deck with milestones and expert responsibilities.

Link to CRM (Airtable/Notion) for investor tracking.

✅ End of Codex Reference
Copy this entire text into Codex or VS Code as a markdown or text file.
When executed alongside the Python model (realestate_portfolio_model.py), it fully reconstructs your project setup, assumptions, expert plan, and investor communication playbook.
