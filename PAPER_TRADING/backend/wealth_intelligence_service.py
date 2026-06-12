from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


CORE_ETF_KEYWORDS = {"ETF", "BALANCED", "GLOBAL EQUITY", "US EQUITY", "CANADA EQUITY", "DEVELOPED MARKETS"}
HIGH_RISK_SECTORS = {"Crypto", "Crypto ETF", "Crypto Infrastructure"}
SIGNAL_POINTS = {
    "fresh": Decimal("26"),
    "strict": Decimal("20"),
    "near": Decimal("10"),
    "none": Decimal("-8"),
}
MARKET_CONTEXT = [
    {
        "category": "Advisor copilot",
        "reference": "Morgan Stanley AI assistant and Debrief",
        "signal": "Large wealth platforms are using AI first to retrieve knowledge, summarize meetings, draft follow-ups, and support advisors rather than replacing registered advisors.",
        "product_implication": "Prioritize advisor-facing research notes, meeting-ready portfolio commentary, and human approval workflows before autonomous investing.",
        "source": "https://www.morganstanley.com/press-releases/ai-at-morgan-stanley-debrief-launch",
    },
    {
        "category": "Portfolio risk commentary",
        "reference": "BlackRock Aladdin Wealth AI commentary",
        "signal": "Institutional wealth technology is moving toward AI-generated portfolio narratives layered on top of risk analytics.",
        "product_implication": "Add explainable portfolio commentary, risk flags, and benchmark-relative narratives for each model basket.",
        "source": "https://www.blackrock.com/aladdin/discover/aladdin-wealth-launches-ai-enabled-commentary-tool-at-morgan-stanley",
    },
    {
        "category": "Advisor platform automation",
        "reference": "Betterment advisor platform expansion",
        "signal": "Advisor platforms are expanding model marketplaces, direct indexing, onboarding automation, and flexible human/automated portfolio controls.",
        "product_implication": "Keep model baskets exportable and build toward advisor-demo workflows rather than only a consumer robo-advisor screen.",
        "source": "https://www.barrons.com/advisor/articles/betterment-ramps-up-portfolio-offerings-for-advisors-6a227a6c",
    },
    {
        "category": "Canadian AI governance",
        "reference": "CSA Staff Notice and Consultation 11-348",
        "signal": "Canadian securities regulators expect AI users to address governance, supervision, conflicts, disclosure, data quality, and investor protection.",
        "product_implication": "Keep AI outputs explainable, dated, supervised, and clearly separated from personalized advice or trade execution.",
        "source": "https://www.osc.ca/en/securities-law/instruments-rules-policies/1/11-348/csa-staff-notice-and-consultation-11-348-applicability-canadian-securities-laws-and-use-artificial",
    },
    {
        "category": "Material AI strategy disclosure",
        "reference": "CSA/market commentary on AI as material fund strategy",
        "signal": "If an investment fund markets AI as a material investment strategy, that use should be clearly disclosed and controlled.",
        "product_implication": "Use precise language: AI-assisted, human-supervised research and risk intelligence until a registered structure and disclosure package exist.",
        "source": "https://www.osler.com/en/insights/blogs/risk/navigating-ai-systems-in-capital-markets-recent-guidance-from-the-csa/",
    },
]


def decimal_value(value: object, default: Decimal = Decimal("0")) -> Decimal:
    try:
        if value is None or value == "":
            return default
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def clamp(value: Decimal, low: Decimal = Decimal("0"), high: Decimal = Decimal("100")) -> Decimal:
    return max(low, min(high, value))


def as_float(value: Decimal) -> float:
    return round(float(value), 6)


def signal_classification(row: dict[str, Any]) -> str:
    signal = row.get("signal")
    if not isinstance(signal, dict) or signal.get("classification") == "none":
        return "none"
    if signal.get("fresh_priority"):
        return "fresh"
    classification = str(signal.get("classification") or "none")
    return classification if classification in {"strict", "near"} else "none"


def ai_wealth_score(row: dict[str, Any]) -> dict[str, Any]:
    signal = row.get("signal") if isinstance(row.get("signal"), dict) else {}
    classification = signal_classification(row)
    overall_score = decimal_value(signal.get("overall_score"), Decimal("35"))
    relative_strength = decimal_value(signal.get("five_day_relative_strength_pct"))
    volume_ratio = decimal_value(signal.get("five_day_volume_ratio"), Decimal("1"))
    monthly = decimal_value(row.get("monthly_change_pct"))
    daily = decimal_value(row.get("daily_change_pct"))
    distance_to_high = decimal_value(signal.get("distance_to_20d_high_pct"))

    raw = Decimal("35")
    raw += SIGNAL_POINTS.get(classification, Decimal("-8"))
    raw += min(overall_score, Decimal("100")) * Decimal("0.22")
    raw += max(Decimal("-12"), min(Decimal("18"), relative_strength * Decimal("1.1")))
    raw += max(Decimal("-5"), min(Decimal("10"), (volume_ratio - Decimal("1")) * Decimal("5")))
    raw += max(Decimal("-8"), min(Decimal("10"), monthly * Decimal("0.25")))
    raw += max(Decimal("-8"), min(Decimal("6"), daily * Decimal("0.7")))
    if distance_to_high > Decimal("12"):
        raw -= min(Decimal("12"), (distance_to_high - Decimal("12")) * Decimal("0.8"))

    score = clamp(raw)
    return {
        "score": as_float(score),
        "classification": classification,
        "drivers": [
            f"{classification} technical signal",
            f"{as_float(relative_strength)}% 5D relative strength vs SPY",
            f"{as_float(volume_ratio)}x 5D volume ratio",
            f"{as_float(monthly)}% monthly move",
        ],
    }


def risk_bucket(row: dict[str, Any], score: float) -> str:
    sector = str(row.get("sector") or "")
    security_type = str(row.get("security_type") or "").casefold()
    monthly = abs(decimal_value(row.get("monthly_change_pct")))
    daily = abs(decimal_value(row.get("daily_change_pct")))
    if security_type == "crypto" or sector in HIGH_RISK_SECTORS or monthly >= Decimal("35") or daily >= Decimal("12"):
        return "high"
    if security_type == "etf" or any(keyword in sector.upper() for keyword in CORE_ETF_KEYWORDS):
        return "core"
    if score >= 78:
        return "satellite"
    return "watchlist"


def candidate_action(bucket: str, classification: str, score: float) -> str:
    if bucket == "high":
        return "risk_review"
    if score >= 80 and classification in {"fresh", "strict"}:
        return "model_candidate"
    if score >= 68:
        return "watchlist_candidate"
    return "monitor"


def build_candidates(stocks: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in stocks:
        if row.get("warning"):
            continue
        scored = ai_wealth_score(row)
        score = float(scored["score"])
        classification = str(scored["classification"])
        bucket = risk_bucket(row, score)
        candidates.append(
            {
                "ticker": row.get("ticker"),
                "security_type": row.get("security_type"),
                "sector": row.get("sector") or "Unclassified",
                "score": score,
                "signal": classification,
                "risk_bucket": bucket,
                "suggested_action": candidate_action(bucket, classification, score),
                "return_pct": row.get("return_pct"),
                "daily_change_pct": row.get("daily_change_pct"),
                "five_day_change_pct": row.get("five_day_change_pct"),
                "monthly_change_pct": row.get("monthly_change_pct"),
                "drivers": scored["drivers"],
                "wealthsimple": row.get("wealthsimple"),
            }
        )
    candidates.sort(
        key=lambda row: (
            row["suggested_action"] == "model_candidate",
            row["score"],
            decimal_value(row.get("monthly_change_pct")),
        ),
        reverse=True,
    )
    return candidates[:limit]


def build_theme_rows(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        grouped.setdefault(str(row["sector"]), []).append(row)
    themes: list[dict[str, Any]] = []
    for sector, rows in grouped.items():
        average_score = sum(float(row["score"]) for row in rows) / len(rows)
        themes.append(
            {
                "theme": sector,
                "candidate_count": len(rows),
                "average_score": round(average_score, 2),
                "model_candidates": sum(row["suggested_action"] == "model_candidate" for row in rows),
                "high_risk_count": sum(row["risk_bucket"] == "high" for row in rows),
                "top_tickers": [str(row["ticker"]) for row in rows[:5]],
            }
        )
    themes.sort(key=lambda row: (row["model_candidates"], row["average_score"]), reverse=True)
    return themes[:10]


def build_basket_models(baskets: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for basket in baskets.get("baskets", []):
        if basket.get("status") == "archived":
            continue
        rows.append(
            {
                "basket_id": basket.get("basket_id"),
                "name": basket.get("basket_name"),
                "status": basket.get("status"),
                "benchmark": basket.get("benchmark"),
                "member_count": basket.get("member_count", 0),
                "rebalance_frequency": basket.get("rebalance_frequency"),
                "role": "model_theme" if basket.get("status") == "active" else "research_theme",
                "notes": basket.get("notes"),
            }
        )
    rows.sort(key=lambda row: (row["role"] == "model_theme", row["member_count"]), reverse=True)
    return rows


def build_business_readiness(overview: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = overview.get("dashboard_metrics") or {}
    signal_mix = metrics.get("signal_mix") or {}
    model_candidates = sum(row["suggested_action"] == "model_candidate" for row in candidates)
    high_risk = sum(row["risk_bucket"] == "high" for row in candidates)
    readiness_score = Decimal("35")
    readiness_score += Decimal(model_candidates) * Decimal("4")
    readiness_score += Decimal(signal_mix.get("fresh", 0)) * Decimal("1.5")
    readiness_score += Decimal(signal_mix.get("strict", 0))
    readiness_score -= Decimal(high_risk) * Decimal("2")
    readiness_score = clamp(readiness_score)
    return {
        "score": as_float(readiness_score),
        "stage": "research_mvp" if readiness_score < 65 else "advisor_demo_ready",
        "strengths": [
            "CFA-led investment framing can sit above the signal engine.",
            "Existing dashboard already tracks signals, baskets, strategy previews, sectors, and research notes.",
            "Outputs are structured enough for advisor demos and model-governance documentation.",
        ],
        "gaps": [
            "No client suitability, KYC, account opening, custody, or order-management workflow is included.",
            "AI scoring is a research layer; it does not create discretionary trades.",
            "Performance claims need audited/controlled track records before external marketing.",
        ],
    }


def wealth_intelligence_response(
    overview: dict[str, Any],
    baskets: dict[str, Any],
    start: date,
    end: date | None,
) -> dict[str, Any]:
    candidates = build_candidates(list(overview.get("stocks") or []))
    return {
        "from_date": start.isoformat(),
        "to_date": end.isoformat() if end else overview.get("to_date"),
        "latest_available_date": overview.get("latest_available_date"),
        "positioning": {
            "business_name_placeholder": "AI Wealth Intelligence",
            "recommended_claim": "CFA-led, human-supervised, AI-assisted portfolio research and risk intelligence.",
            "avoid_claims": [
                "Do not claim guaranteed returns.",
                "Do not imply fully autonomous client portfolio management.",
                "Do not market backtests as live audited performance.",
            ],
        },
        "business_readiness": build_business_readiness(overview, candidates),
        "operating_model": [
            "Research engine ranks securities and themes from market data, signal strength, relative strength, and risk flags.",
            "Human review approves model themes and any external communication.",
            "Registered partner or future registered PM/IFM handles client advice, suitability, custody, and trading.",
        ],
        "model_baskets": build_basket_models(baskets),
        "market_context": MARKET_CONTEXT,
        "theme_opportunities": build_theme_rows(candidates),
        "ai_signal_candidates": candidates,
        "risk_controls": [
            "Use model outputs as research only until registration or a registered partner is in place.",
            "Separate model-candidate status from any real client recommendation.",
            "Keep explainable signal drivers for every candidate.",
            "Flag high-risk crypto, single-name volatility, and overextended momentum before marketing a theme.",
            "Preserve dated snapshots so future claims can be tied to exact source data.",
        ],
        "next_build_steps": [
            "Add persistent dated wealth-intelligence snapshots.",
            "Add model portfolio fact sheets for selected baskets.",
            "Add backtest-vs-benchmark reports with drawdown, volatility, turnover, and assumptions.",
            "Add advisor-demo export with compliance footnotes.",
            "Add optional LLM narrative generation behind a human-review queue.",
        ],
        "disclaimer": (
            "Research workspace output only. This endpoint does not provide personalized investment advice, "
            "does not assess suitability, and does not create broker orders or client portfolios."
        ),
    }
