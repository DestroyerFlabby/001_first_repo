from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import sqrt
from typing import Callable, Iterable

from backend.dashboard_service import fetch_chart, yahoo_symbol


SCHEMA_VERSION = "1.0"
CALCULATION_VERSION = "correlation-overlap-1.0"
MAX_INTERACTIVE_POSITIONS = 12
DEFAULT_MINIMUM_OBSERVATIONS = 20
PriceLoader = Callable[[str, str, date, date], dict[date, float]]


def position_values(detail: dict[str, object]) -> dict[str, float]:
    values: defaultdict[str, float] = defaultdict(float)
    positions = detail.get("positions")
    if not isinstance(positions, list):
        return {}
    for row in positions:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        value = float(row.get("current_value") or 0)
        if ticker and value > 0:
            values[ticker] += value
    return dict(values)


def top_positions(detail: dict[str, object], limit: int = MAX_INTERACTIVE_POSITIONS) -> list[dict[str, object]]:
    values = position_values(detail)
    total = sum(values.values())
    rows = [
        {"ticker": ticker, "current_value": value, "weight_pct": value / total * 100 if total else 0.0}
        for ticker, value in values.items()
    ]
    return sorted(rows, key=lambda row: (-float(row["current_value"]), str(row["ticker"])))[:limit]


def close_returns(prices: dict[date, float]) -> dict[date, float]:
    ordered = sorted((day, float(value)) for day, value in prices.items() if float(value) > 0)
    returns: dict[date, float] = {}
    for (previous_day, previous), (current_day, current) in zip(ordered, ordered[1:]):
        del previous_day
        if previous:
            returns[current_day] = current / previous - 1
    return returns


def pair_correlation(
    left: dict[date, float],
    right: dict[date, float],
    minimum_observations: int = DEFAULT_MINIMUM_OBSERVATIONS,
) -> dict[str, object]:
    dates = sorted(set(left) & set(right))
    if len(dates) < minimum_observations:
        return {"correlation": None, "observations": len(dates), "warning": "insufficient aligned history"}
    left_values = [left[day] for day in dates]
    right_values = [right[day] for day in dates]
    left_mean = sum(left_values) / len(left_values)
    right_mean = sum(right_values) / len(right_values)
    left_variance = sum((value - left_mean) ** 2 for value in left_values)
    right_variance = sum((value - right_mean) ** 2 for value in right_values)
    if left_variance == 0 or right_variance == 0:
        return {"correlation": None, "observations": len(dates), "warning": "zero-variance return series"}
    covariance = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_values, right_values)
    )
    correlation = covariance / sqrt(left_variance * right_variance)
    return {"correlation": max(-1.0, min(1.0, correlation)), "observations": len(dates), "warning": None}


def default_price_loader(ticker: str, asset_type: str, start: date, end: date) -> dict[date, float]:
    _, bars = fetch_chart(yahoo_symbol(ticker, asset_type or "stock"))
    return {bar.day: float(bar.close) for bar in bars if start <= bar.day <= end}


def diversification_warning(valid_pairs: list[dict[str, object]], security_count: int) -> str | None:
    if security_count < 2:
        return "Fewer than two positions have usable values; correlation cannot assess diversification."
    correlations = [float(row["correlation"]) for row in valid_pairs]
    if not correlations:
        return "No pair has enough non-zero-variance aligned history for correlation analysis."
    average = sum(correlations) / len(correlations)
    high_share = sum(value >= 0.8 for value in correlations) / len(correlations)
    if average >= 0.7 or high_share >= 0.5:
        return "The selected positions move together strongly; a high security count may overstate diversification."
    return None


def correlation_response(
    portfolio_detail: dict[str, object],
    start: date,
    end: date,
    *,
    price_loader: PriceLoader = default_price_loader,
    minimum_observations: int = DEFAULT_MINIMUM_OBSERVATIONS,
) -> dict[str, object]:
    selected = top_positions(portfolio_detail)
    raw_positions = position_values(portfolio_detail)
    position_types = {
        str(row.get("ticker") or "").strip().upper(): str(
            row.get("security_type") or row.get("asset_type") or "stock"
        ).strip().casefold()
        for row in portfolio_detail.get("positions", [])
        if isinstance(row, dict) and row.get("ticker")
    }
    return_series: dict[str, dict[date, float]] = {}
    warnings: list[str] = []
    for row in selected:
        ticker = str(row["ticker"])
        try:
            prices = price_loader(ticker, position_types.get(ticker, "stock"), start, end)
            returns = close_returns(prices)
            if len(returns) < minimum_observations:
                warnings.append(f"{ticker}: only {len(returns)} close-to-close returns available")
            return_series[ticker] = returns
        except Exception as exc:
            warnings.append(f"{ticker}: price history unavailable: {exc}")
            return_series[ticker] = {}

    pairs: list[dict[str, object]] = []
    tickers = [str(row["ticker"]) for row in selected]
    for index, left in enumerate(tickers):
        for right in tickers[index + 1 :]:
            result = pair_correlation(return_series[left], return_series[right], minimum_observations)
            pairs.append({"left": left, "right": right, **result})
    valid_pairs = [row for row in pairs if row["correlation"] is not None]
    valid_pairs.sort(key=lambda row: float(row["correlation"]), reverse=True)
    correlations = [float(row["correlation"]) for row in valid_pairs]
    omitted_count = max(len(raw_positions) - len(selected), 0)
    if omitted_count:
        warnings.append(f"Limited interactive analysis to the top {len(selected)} positions; omitted {omitted_count} smaller positions.")

    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "portfolio": str(portfolio_detail.get("investor") or portfolio_detail.get("portfolio_name") or "Selected portfolio"),
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
        "selected_positions": selected,
        "selected_position_count": len(selected),
        "total_position_count": len(raw_positions),
        "minimum_observations": minimum_observations,
        "pairwise_correlations": pairs,
        "average_correlation": sum(correlations) / len(correlations) if correlations else None,
        "highest_correlation_pairs": valid_pairs[:5],
        "lowest_correlation_pairs": list(reversed(valid_pairs[-5:])),
        "diversification_warning": diversification_warning(valid_pairs, len(selected)),
        "data_quality": {
            "warnings": warnings,
            "valid_pair_count": len(valid_pairs),
            "unavailable_pair_count": len(pairs) - len(valid_pairs),
            "assumptions": [
                "Correlation uses aligned close-to-close returns and does not fill missing dates.",
                "Interactive analysis is limited to the 12 largest current positions.",
                "Correlation is historical co-movement, not a forecast or guarantee of diversification.",
                "ETF look-through overlap is unavailable.",
            ],
            "source_labels": ["portfolio_detail.positions", "dashboard_service.fetch_chart"],
        },
    }


def direct_overlap_response(left_detail: dict[str, object], right_detail: dict[str, object]) -> dict[str, object]:
    left = position_values(left_detail)
    right = position_values(right_detail)
    left_total = sum(left.values())
    right_total = sum(right.values())
    shared = sorted(set(left) & set(right))
    rows = []
    for ticker in shared:
        left_weight = left[ticker] / left_total * 100 if left_total else 0.0
        right_weight = right[ticker] / right_total * 100 if right_total else 0.0
        rows.append(
            {
                "ticker": ticker,
                "left_value": left[ticker],
                "right_value": right[ticker],
                "left_weight_pct": left_weight,
                "right_weight_pct": right_weight,
                "minimum_shared_weight_pct": min(left_weight, right_weight),
            }
        )
    rows.sort(key=lambda row: (-float(row["minimum_shared_weight_pct"]), str(row["ticker"])))
    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "left_portfolio": str(left_detail.get("investor") or left_detail.get("portfolio_name") or "Left portfolio"),
        "right_portfolio": str(right_detail.get("investor") or right_detail.get("portfolio_name") or "Right portfolio"),
        "shared_security_count": len(rows),
        "shared_tickers": [row["ticker"] for row in rows],
        "direct_overlap_pct": sum(float(row["minimum_shared_weight_pct"]) for row in rows),
        "overlap": rows,
        "etf_lookthrough": {"available": False, "note": "ETF constituent overlap is not available; only direct ticker overlap is measured."},
    }
