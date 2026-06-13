from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from backend.dashboard_service import (
    VARIABLE_STRATEGY_START,
    as_float,
    benchmark_comparison,
    clamp,
    entry_signal,
    fetch_chart,
    fixed_changes_from_series,
    live_signal,
    master_candidate_score,
    on_or_before,
    owners_by_asset,
    pct_change,
    sector_for_asset,
    yahoo_symbol,
)
from backend.macro_statement_service import bank_of_canada_macro_context
from backend.news_strategy import load_daily_news_counts, news_metrics
from backend.universe_service import read_asset_universe


MODEL_PORTFOLIO_NAME = "systematic-model-portfolio"
MODEL_PORTFOLIO_V2_NAME = "systematic-model-portfolio-2"
MODEL_PORTFOLIO_V3_NAME = "systematic-model-portfolio-3"
MODEL_PORTFOLIO_V4_NAME = "systematic-model-portfolio-4"
MODEL_INITIAL_CAPITAL = Decimal("100000")
MODEL_INVESTED_TARGET = Decimal("0.95")
MODEL_MAX_POSITIONS = 25
MODEL_MAX_NAME_WEIGHT = Decimal("0.07")
MODEL_MAX_SECTOR_WEIGHT = Decimal("0.25")
MODEL_MAX_NAMES_PER_SECTOR = 5
MODEL_REBALANCE_BAND = Decimal("0.03")
MODEL_MIN_SCORE = Decimal("50")
MODEL_NEAR_MIN_SCORE = Decimal("75")
MODEL_EXIT_BUFFER_SESSIONS = 10
MODEL_V2_SOFT_DRAWDOWN = Decimal("-8")
MODEL_V2_MEDIUM_DRAWDOWN = Decimal("-12")
MODEL_V2_HARD_DRAWDOWN = Decimal("-18")
MODEL_V2_HIGH_VOLATILITY = Decimal("80")
MODEL_V3_MIN_SELL_DRAWDOWN = Decimal("-7")
MODEL_V3_MAX_SELL_DRAWDOWN = Decimal("-20")
MODEL_V3_DRAWDOWN_MULTIPLIER = Decimal("2.50")
MODEL_V4_INTRADAY_PROXY_MULTIPLIER = Decimal("0.75")


def _asset_available(row: dict[str, object], observed_day: date) -> bool:
    if str(row.get("asset_type") or "").casefold() != "stock":
        return False
    if not bool(row.get("strategy_eligible")):
        return False
    status = str(row.get("status") or "").casefold()
    if status in {"excluded", "benchmark"}:
        return False
    added_at = str(row.get("added_at") or "")
    if added_at and date.fromisoformat(added_at) > observed_day:
        return False
    archived_at = str(row.get("archived_at") or "")
    if archived_at:
        return date.fromisoformat(archived_at) > observed_day
    return status != "archived"


def _asset_ever_available(row: dict[str, object], end: date) -> bool:
    if str(row.get("asset_type") or "").casefold() != "stock" or not bool(row.get("strategy_eligible")):
        return False
    if str(row.get("status") or "").casefold() in {"excluded", "benchmark"}:
        return False
    added_at = str(row.get("added_at") or "")
    if added_at and date.fromisoformat(added_at) > end:
        return False
    archived_at = str(row.get("archived_at") or "")
    return not archived_at or date.fromisoformat(archived_at) > VARIABLE_STRATEGY_START


def _trailing_volatility(bars: tuple[object, ...]) -> Decimal:
    closes = [Decimal(str(bar.close)) for bar in bars[-21:]]
    if len(closes) < 6:
        return Decimal("0")
    returns = [float(pct_change(current, previous)) for previous, current in zip(closes, closes[1:])]
    if len(returns) < 2:
        return Decimal("0")
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    return Decimal(str(math.sqrt(variance) * math.sqrt(252)))


def _candidate_score(
    signal: dict[str, object],
    category: str,
    news: dict[str, Decimal | int | None],
    volatility_pct: Decimal,
) -> tuple[Decimal, dict[str, float]]:
    base = master_candidate_score(signal, category, news)
    horizons = signal.get("horizons", {}) if isinstance(signal.get("horizons"), dict) else {}
    one_month = horizons.get("1m", {}) if isinstance(horizons.get("1m"), dict) else {}
    three_month = horizons.get("3m", {}) if isinstance(horizons.get("3m"), dict) else {}
    one_month_relative = Decimal(str(one_month.get("relative_strength_pct", 0)))
    three_month_relative = Decimal(str(three_month.get("relative_strength_pct", 0)))
    confirmation_bonus = Decimal("0")
    for horizon in horizons.values():
        if not isinstance(horizon, dict):
            continue
        if Decimal(str(horizon.get("relative_strength_pct", 0))) > 0 and Decimal(str(horizon.get("score", 0))) >= 45:
            confirmation_bonus += Decimal("2")
    medium_term_bonus = clamp(one_month_relative, Decimal("-10"), Decimal("20")) * Decimal("0.35")
    medium_term_bonus += clamp(three_month_relative, Decimal("-10"), Decimal("25")) * Decimal("0.15")
    volatility_penalty = clamp((volatility_pct - Decimal("35")) * Decimal("0.25"), Decimal("0"), Decimal("18"))
    final_score = base + confirmation_bonus + medium_term_bonus - volatility_penalty
    return final_score, {
        "base_signal_score": as_float(base),
        "confirmation_bonus": as_float(confirmation_bonus),
        "medium_term_bonus": as_float(medium_term_bonus),
        "volatility_penalty": as_float(volatility_penalty),
        "annualized_volatility_pct": as_float(volatility_pct),
    }


def _horizon_value(signal: dict[str, object], horizon: str, key: str, default: str = "0") -> Decimal:
    horizons = signal.get("horizons", {}) if isinstance(signal.get("horizons"), dict) else {}
    row = horizons.get(horizon, {}) if isinstance(horizons.get(horizon), dict) else {}
    try:
        return Decimal(str(row.get(key, default)))
    except Exception:
        return Decimal(default)


def _select_candidates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(rows, key=lambda row: (Decimal(str(row["model_score"])), str(row["ticker"])), reverse=True)
    selected: list[dict[str, object]] = []
    selected_tickers: set[str] = set()
    sector_counts: defaultdict[str, int] = defaultdict(int)

    # Seed sector breadth before filling remaining slots by score.
    for row in ranked:
        sector = str(row["sector"])
        ticker = str(row["ticker"])
        if sector_counts[sector] or len(selected) >= MODEL_MAX_POSITIONS:
            continue
        selected.append(row)
        selected_tickers.add(ticker)
        sector_counts[sector] += 1

    for row in ranked:
        ticker = str(row["ticker"])
        sector = str(row["sector"])
        if ticker in selected_tickers or len(selected) >= MODEL_MAX_POSITIONS:
            continue
        if sector_counts[sector] >= MODEL_MAX_NAMES_PER_SECTOR:
            continue
        selected.append(row)
        selected_tickers.add(ticker)
        sector_counts[sector] += 1
    return selected


def _target_weights(rows: list[dict[str, object]]) -> dict[str, Decimal]:
    if not rows:
        return {}
    scores = [Decimal(str(row["model_score"])) for row in rows]
    center = Decimal(str(median(scores)))
    raw = {
        str(row["ticker"]): Decimal("1")
        + clamp((Decimal(str(row["model_score"])) - center) / Decimal("80"), Decimal("-0.25"), Decimal("0.50"))
        for row in rows
    }
    total_raw = sum(raw.values(), Decimal("0"))
    weights = {
        ticker: min(value / total_raw * MODEL_INVESTED_TARGET, MODEL_MAX_NAME_WEIGHT)
        for ticker, value in raw.items()
    }
    sectors = {str(row["ticker"]): str(row["sector"]) for row in rows}
    sector_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for ticker, weight in weights.items():
        sector_totals[sectors[ticker]] += weight
    for sector, total in sector_totals.items():
        if total <= MODEL_MAX_SECTOR_WEIGHT:
            continue
        scale = MODEL_MAX_SECTOR_WEIGHT / total
        for ticker in weights:
            if sectors[ticker] == sector:
                weights[ticker] *= scale
    return weights


def _position_drawdown_pct(
    ticker: str,
    holding: dict[str, object],
    observed_day: date,
    charts: dict[str, tuple[object, ...]],
) -> Decimal:
    price_bar = on_or_before(charts[ticker], observed_day)
    if not price_bar:
        return Decimal("0")
    peak_price = Decimal(str(holding.get("peak_price") or price_bar.close))
    if peak_price <= 0:
        return Decimal("0")
    return pct_change(price_bar.close, peak_price)


def _drawdown_adjusted_weights(
    observed_day: date,
    selected: list[dict[str, object]],
    weights: dict[str, Decimal],
    current_holdings: dict[str, dict[str, object]],
    charts: dict[str, tuple[object, ...]],
) -> dict[str, Decimal]:
    selected_by_ticker = {str(row["ticker"]): row for row in selected}
    adjusted = dict(weights)
    for ticker, holding in current_holdings.items():
        if ticker not in adjusted:
            continue
        row = selected_by_ticker.get(ticker, {})
        drawdown_pct = _position_drawdown_pct(ticker, holding, observed_day, charts)
        volume_ratio = Decimal(str(row.get("five_day_volume_ratio", 1)))
        one_month_relative = Decimal(str(row.get("one_month_relative_strength_pct", 0)))
        signal = str(row.get("entry_signal") or holding.get("entry_signal") or "")
        news_active = bool(row.get("news_active"))
        news_accelerating = bool(row.get("news_accelerating"))
        strong_support = (
            signal in {"fresh", "strict"}
            and volume_ratio >= Decimal("1.15")
            and one_month_relative >= Decimal("0")
            and (news_active or news_accelerating)
        )
        weak_confirmation = volume_ratio < Decimal("1") or one_month_relative < Decimal("-3")
        reason = ""
        if drawdown_pct <= MODEL_V2_HARD_DRAWDOWN and not strong_support:
            adjusted[ticker] = Decimal("0")
            reason = "hard drawdown exit: position drawdown lacks fresh/strict signal, volume, momentum, and news support"
        elif drawdown_pct <= MODEL_V2_MEDIUM_DRAWDOWN and (weak_confirmation or not news_active):
            adjusted[ticker] *= Decimal("0.50")
            reason = "medium drawdown trim: confirmation weakened"
        elif drawdown_pct <= MODEL_V2_SOFT_DRAWDOWN and weak_confirmation:
            adjusted[ticker] *= Decimal("0.75")
            reason = "soft drawdown trim: weak volume or one-month relative strength"
        if reason:
            holding["drawdown_control_reason"] = reason
            holding["drawdown_control_observed_date"] = observed_day.isoformat()
            holding["drawdown_control_drawdown_pct"] = as_float(drawdown_pct)
            holding["drawdown_control_target_weight_pct"] = as_float(adjusted[ticker] * 100)

    for row in selected:
        ticker = str(row["ticker"])
        if ticker in current_holdings or ticker not in adjusted:
            continue
        volatility = Decimal(str(row.get("score_components", {}).get("annualized_volatility_pct", 0)))
        if volatility >= MODEL_V2_HIGH_VOLATILITY and str(row.get("entry_signal")) == "near":
            adjusted[ticker] *= Decimal("0.50")
    return adjusted


def _average_daily_drawdown_pct(holding: dict[str, object]) -> Decimal:
    values = [
        Decimal(str(value))
        for value in holding.get("daily_adverse_moves_pct", [])
        if Decimal(str(value)) < 0
    ]
    if not values:
        return Decimal("-3")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _average_drawdown_sell_point_pct(holding: dict[str, object], intraday_proxy: bool = False) -> Decimal:
    average_adverse = _average_daily_drawdown_pct(holding)
    threshold = average_adverse * MODEL_V3_DRAWDOWN_MULTIPLIER
    threshold = max(MODEL_V3_MAX_SELL_DRAWDOWN, min(MODEL_V3_MIN_SELL_DRAWDOWN, threshold))
    if intraday_proxy:
        threshold *= MODEL_V4_INTRADAY_PROXY_MULTIPLIER
    return threshold


def _average_drawdown_adjusted_weights(
    observed_day: date,
    selected: list[dict[str, object]],
    weights: dict[str, Decimal],
    current_holdings: dict[str, dict[str, object]],
    charts: dict[str, tuple[object, ...]],
    intraday_proxy: bool = False,
) -> dict[str, Decimal]:
    adjusted = _drawdown_adjusted_weights(observed_day, selected, weights, current_holdings, charts)
    selected_by_ticker = {str(row["ticker"]): row for row in selected}
    for ticker, holding in current_holdings.items():
        if ticker not in adjusted:
            continue
        row = selected_by_ticker.get(ticker, {})
        drawdown_pct = _position_drawdown_pct(ticker, holding, observed_day, charts)
        sell_point = _average_drawdown_sell_point_pct(holding, intraday_proxy=intraday_proxy)
        volume_ratio = Decimal(str(row.get("five_day_volume_ratio", 1)))
        one_month_relative = Decimal(str(row.get("one_month_relative_strength_pct", 0)))
        news_active = bool(row.get("news_active"))
        signal = str(row.get("entry_signal") or holding.get("entry_signal") or "")
        weak_confirmation = volume_ratio < Decimal("1.05") or one_month_relative < Decimal("0") or signal == "near"
        reason = ""
        if drawdown_pct <= sell_point and (weak_confirmation or not news_active):
            adjusted[ticker] = Decimal("0")
            reason = (
                "average daily drawdown sell point"
                if not intraday_proxy
                else "intraday proxy drawdown sell point"
            )
        elif drawdown_pct <= sell_point * Decimal("0.80") and weak_confirmation:
            adjusted[ticker] *= Decimal("0.50")
            reason = (
                "average daily drawdown trim point"
                if not intraday_proxy
                else "intraday proxy drawdown trim point"
            )
        if reason:
            holding["drawdown_control_reason"] = (
                f"{reason}: current {as_float(drawdown_pct)}% vs sell point {as_float(sell_point)}%"
            )
            holding["drawdown_control_observed_date"] = observed_day.isoformat()
            holding["drawdown_control_drawdown_pct"] = as_float(drawdown_pct)
            holding["drawdown_control_sell_point_pct"] = as_float(sell_point)
            holding["drawdown_control_target_weight_pct"] = as_float(adjusted[ticker] * 100)
    return adjusted


def systematic_model_portfolio_response(end: date | None = None) -> dict[str, object]:
    return _systematic_model_portfolio_response(end, risk_mode="base")


def systematic_model_portfolio_v2_response(end: date | None = None) -> dict[str, object]:
    return _systematic_model_portfolio_response(end, risk_mode="v2")


def systematic_model_portfolio_v3_response(end: date | None = None) -> dict[str, object]:
    return _systematic_model_portfolio_response(end, risk_mode="v3")


def systematic_model_portfolio_v4_response(end: date | None = None) -> dict[str, object]:
    return _systematic_model_portfolio_response(end, risk_mode="v4")


def _systematic_model_portfolio_response(end: date | None = None, risk_mode: str = "base") -> dict[str, object]:
    portfolio_name = {
        "base": MODEL_PORTFOLIO_NAME,
        "v2": MODEL_PORTFOLIO_V2_NAME,
        "v3": MODEL_PORTFOLIO_V3_NAME,
        "v4": MODEL_PORTFOLIO_V4_NAME,
    }.get(risk_mode, MODEL_PORTFOLIO_NAME)
    universe = read_asset_universe()
    owners = owners_by_asset()
    _, market_bars = fetch_chart("SPY")
    latest_market = on_or_before(market_bars, end)
    if not latest_market or latest_market.day < VARIABLE_STRATEGY_START:
        raise ValueError("model portfolio requires an ending market date on or after 2026-01-31")
    sessions = [bar.day for bar in market_bars if VARIABLE_STRATEGY_START <= bar.day <= latest_market.day]
    if not sessions:
        raise ValueError("missing model portfolio market sessions")

    latest_eligible = [row for row in universe if _asset_ever_available(row, latest_market.day)]
    charts: dict[str, tuple[object, ...]] = {}
    asset_types: dict[str, str] = {}
    sectors: dict[str, str] = {}
    added_dates: dict[str, date] = {}
    universe_by_ticker: dict[str, dict[str, object]] = {}
    for row in latest_eligible:
        ticker = str(row["ticker"])
        asset_type = str(row["asset_type"])
        try:
            _, bars = fetch_chart(yahoo_symbol(ticker, asset_type))
        except Exception:
            continue
        if not bars:
            continue
        charts[ticker] = bars
        universe_by_ticker[ticker] = row
        asset_types[ticker] = asset_type
        configured_sector = str(row.get("sector") or "").strip()
        sectors[ticker] = configured_sector or sector_for_asset(
            ticker,
            asset_type,
            owners.get((ticker, asset_type), [MODEL_PORTFOLIO_NAME]),
        )[0]
        added_dates[ticker] = date.fromisoformat(str(row.get("added_at") or VARIABLE_STRATEGY_START.isoformat()))

    daily_news = load_daily_news_counts()
    news_counts = daily_news.get("tickers", {})
    if not isinstance(news_counts, dict):
        news_counts = {}

    def candidates(observed_day: date) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for ticker, bars in charts.items():
            if added_dates[ticker] > observed_day or not _asset_available(universe_by_ticker[ticker], observed_day):
                continue
            signal_bars = tuple(bar for bar in bars if bar.day <= observed_day)
            signal = live_signal(signal_bars)
            category = entry_signal(signal)
            if not category or not isinstance(signal, dict):
                continue
            ticker_counts = news_counts.get(ticker, {})
            news = news_metrics(ticker_counts if isinstance(ticker_counts, dict) else {}, observed_day)
            volatility = _trailing_volatility(signal_bars)
            score, score_components = _candidate_score(signal, category, news, volatility)
            minimum_score = MODEL_NEAR_MIN_SCORE if category == "near" else MODEL_MIN_SCORE
            if score < minimum_score:
                continue
            rows.append(
                {
                    "ticker": ticker,
                    "asset_type": asset_types[ticker],
                    "sector": sectors[ticker],
                    "entry_signal": category,
                    "model_score": score,
                    "signal_score": signal.get("overall_score", 0),
                    "news_articles_7d": int(news["articles_7d"]),
                    "news_articles_prior_7d": int(news["articles_prior_7d"]),
                    "news_active": int(news["articles_7d"]) > 0,
                    "news_accelerating": int(news["articles_7d"]) > int(news["articles_prior_7d"]),
                    "five_day_volume_ratio": as_float(_horizon_value(signal, "5d", "volume_ratio", "1")),
                    "five_day_relative_strength_pct": as_float(_horizon_value(signal, "5d", "relative_strength_pct")),
                    "one_month_relative_strength_pct": as_float(_horizon_value(signal, "1m", "relative_strength_pct")),
                    "score_components": score_components,
                }
            )
        return _select_candidates(rows)

    def portfolio_targets(
        observed_day: date,
        current_holdings: dict[str, dict[str, object]],
        update_streaks: bool,
    ) -> tuple[list[dict[str, object]], dict[str, Decimal]]:
        ranked = candidates(observed_day)
        ranked_by_ticker = {str(row["ticker"]): row for row in ranked}
        retained: list[dict[str, object]] = []
        retained_tickers: set[str] = set()
        for ticker, holding in current_holdings.items():
            qualifying = ranked_by_ticker.get(ticker)
            if qualifying:
                if update_streaks:
                    holding["below_model_streak"] = 0
                retained.append(qualifying)
                retained_tickers.add(ticker)
                continue
            streak = int(holding.get("below_model_streak", 0)) + 1
            if update_streaks:
                holding["below_model_streak"] = streak
            if streak >= MODEL_EXIT_BUFFER_SESSIONS:
                continue
            retained.append(
                {
                    "ticker": ticker,
                    "asset_type": asset_types[ticker],
                    "sector": holding.get("sector", sectors.get(ticker, "Unclassified")),
                    "entry_signal": holding.get("entry_signal", "unknown"),
                    "model_score": max(
                        Decimal(str(holding.get("model_score", MODEL_MIN_SCORE))) - Decimal(streak * 5),
                        Decimal("1"),
                    ),
                    "signal_score": holding.get("signal_score", 0),
                    "news_articles_7d": holding.get("news_articles_7d", 0),
                    "news_articles_prior_7d": 0,
                    "news_active": False,
                    "news_accelerating": False,
                    "five_day_volume_ratio": 1,
                    "five_day_relative_strength_pct": 0,
                    "one_month_relative_strength_pct": 0,
                    "score_components": {},
                    "retained_buffer": True,
                }
            )
            retained_tickers.add(ticker)

        slots = max(MODEL_MAX_POSITIONS - len(retained), 0)
        new_rows = [row for row in ranked if str(row["ticker"]) not in retained_tickers][:slots]
        selected = retained + new_rows
        weights = _target_weights(selected)
        if risk_mode == "v2":
            weights = _drawdown_adjusted_weights(observed_day, selected, weights, current_holdings, charts)
        elif risk_mode == "v3":
            weights = _average_drawdown_adjusted_weights(
                observed_day, selected, weights, current_holdings, charts, intraday_proxy=False
            )
        elif risk_mode == "v4":
            weights = _average_drawdown_adjusted_weights(
                observed_day, selected, weights, current_holdings, charts, intraday_proxy=True
            )
        return selected, weights

    cash = MODEL_INITIAL_CAPITAL
    holdings: dict[str, dict[str, object]] = {}
    trade_ledger: list[dict[str, object]] = []
    realized_positions: list[dict[str, object]] = []
    series: list[dict[str, object]] = []
    daily_rebalances: list[dict[str, object]] = []
    sector_exposure: list[dict[str, object]] = []
    signal_mix: list[dict[str, object]] = []
    total_traded = Decimal("0")
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))

    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        selected, weights = portfolio_targets(previous_session.day, holdings, update_streaks=True)
        selected_by_ticker = {str(row["ticker"]): row for row in selected}
        for ticker, holding in holdings.items():
            row = selected_by_ticker.get(ticker)
            if not row or row.get("retained_buffer"):
                continue
            holding.update(
                {
                    "entry_signal": row.get("entry_signal", holding.get("entry_signal", "unknown")),
                    "sector": row.get("sector", holding.get("sector", "Unclassified")),
                    "model_score": as_float(Decimal(str(row.get("model_score", 0)))),
                    "signal_score": row.get("signal_score", 0),
                    "news_articles_7d": row.get("news_articles_7d", 0),
                }
            )
        observed_values: dict[str, Decimal] = {}
        observed_equity = cash
        for ticker, holding in holdings.items():
            bar = on_or_before(charts[ticker], previous_session.day)
            if not bar:
                continue
            value = Decimal(str(holding["shares"])) * bar.close
            observed_values[ticker] = value
            observed_equity += value

        orders: list[dict[str, object]] = []
        for ticker in sorted(set(holdings) | set(weights)):
            current_value = observed_values.get(ticker, Decimal("0"))
            target_weight = weights.get(ticker, Decimal("0"))
            target_value = observed_equity * target_weight
            delta = target_value - current_value
            if target_weight and ticker in holdings and observed_equity:
                if abs(delta) / observed_equity < MODEL_REBALANCE_BAND:
                    continue
            candidate = selected_by_ticker.get(ticker)
            if delta > 0 and candidate and candidate.get("retained_buffer"):
                continue
            if abs(delta) < Decimal("1"):
                continue
            orders.append(
                {
                    "ticker": ticker,
                    "action": "buy" if delta > 0 else "sell",
                    "usd_amount": abs(delta),
                    "target_weight": target_weight,
                    "candidate": selected_by_ticker.get(ticker),
                }
            )

        buys = 0
        sells = 0
        traded_today = Decimal("0")
        for order in sorted(orders, key=lambda row: 0 if row["action"] == "sell" else 1):
            ticker = str(order["ticker"])
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar or price_bar.day <= previous_session.day:
                continue
            amount = Decimal(str(order["usd_amount"]))
            candidate = order.get("candidate") or {}
            if order["action"] == "sell":
                holding = holdings.get(ticker)
                if not holding:
                    continue
                available_value = Decimal(str(holding["shares"])) * price_bar.close
                full_exit = Decimal(str(order["target_weight"])) == 0
                sale_value = available_value if full_exit else min(amount, available_value)
                quantity = Decimal(str(holding["shares"])) if full_exit else min(
                    sale_value / price_bar.close,
                    Decimal(str(holding["shares"])),
                )
                allocated_cost = quantity * Decimal(str(holding["average_cost"]))
                realized_pnl = sale_value - allocated_cost
                holding["shares"] = Decimal(str(holding["shares"])) - quantity
                holding["remaining_cost"] = Decimal(str(holding["remaining_cost"])) - allocated_cost
                holding["cumulative_proceeds"] = Decimal(str(holding["cumulative_proceeds"])) + sale_value
                holding["cumulative_realized_pnl"] = Decimal(str(holding["cumulative_realized_pnl"])) + realized_pnl
                cash += sale_value
                sells += 1
                traded_today += sale_value
                trade_ledger.append(
                    {
                        "date": price_bar.day.isoformat(),
                        "signal_observed_date": previous_session.day.isoformat(),
                        "action": "sell",
                        "ticker": ticker,
                        "execution_price": as_float(price_bar.close),
                        "quantity": as_float(quantity),
                        "usd_amount": as_float(sale_value),
                        "realized_gain_loss": as_float(realized_pnl),
                        "target_weight_pct": as_float(Decimal(str(order["target_weight"])) * 100),
                        "reason": holding.get("drawdown_control_reason")
                        or ("removed from model" if not order["target_weight"] else "rebalance band"),
                    }
                )
                if Decimal(str(holding["shares"])) <= Decimal("0.00000001"):
                    realized_positions.append(
                        {
                            "ticker": ticker,
                            "entry_date": holding["entry_date"],
                            "exit_date": price_bar.day.isoformat(),
                            "initial_value": as_float(Decimal(str(holding["initial_cost"]))),
                            "ending_value": as_float(Decimal(str(holding["cumulative_proceeds"]))),
                            "gain_loss": as_float(Decimal(str(holding["cumulative_realized_pnl"]))),
                            "return_pct": as_float(
                                pct_change(
                                    Decimal(str(holding["cumulative_proceeds"])),
                                    Decimal(str(holding["initial_cost"])),
                                )
                            ),
                            "entry_signal": holding["entry_signal"],
                            "sector": holding["sector"],
                            "status": "closed",
                        }
                    )
                    del holdings[ticker]
            else:
                purchase_value = min(amount, cash)
                if purchase_value < Decimal("1"):
                    continue
                quantity = purchase_value / price_bar.close
                holding = holdings.get(ticker)
                if holding:
                    previous_cost = Decimal(str(holding["remaining_cost"]))
                    previous_shares = Decimal(str(holding["shares"]))
                    holding["shares"] = previous_shares + quantity
                    holding["remaining_cost"] = previous_cost + purchase_value
                    holding["initial_cost"] = Decimal(str(holding["initial_cost"])) + purchase_value
                    holding["average_cost"] = (previous_cost + purchase_value) / (previous_shares + quantity)
                else:
                    holdings[ticker] = {
                        "ticker": ticker,
                        "shares": quantity,
                        "average_cost": price_bar.close,
                        "remaining_cost": purchase_value,
                        "initial_cost": purchase_value,
                        "cumulative_proceeds": Decimal("0"),
                        "cumulative_realized_pnl": Decimal("0"),
                        "entry_date": price_bar.day.isoformat(),
                        "entry_signal": candidate.get("entry_signal", "unknown"),
                        "sector": candidate.get("sector", sectors.get(ticker, "Unclassified")),
                        "peak_price": price_bar.close,
                        "max_position_drawdown_pct": Decimal("0"),
                        "last_close": price_bar.close,
                        "daily_adverse_moves_pct": [],
                    }
                holding = holdings[ticker]
                holding.update(
                    {
                        "entry_signal": candidate.get("entry_signal", holding.get("entry_signal", "unknown")),
                        "sector": candidate.get("sector", holding.get("sector", "Unclassified")),
                        "model_score": as_float(Decimal(str(candidate.get("model_score", 0)))),
                        "signal_score": candidate.get("signal_score", 0),
                        "news_articles_7d": candidate.get("news_articles_7d", 0),
                        "target_weight": as_float(Decimal(str(order["target_weight"]))),
                        "below_model_streak": 0,
                    }
                )
                cash -= purchase_value
                buys += 1
                traded_today += purchase_value
                trade_ledger.append(
                    {
                        "date": price_bar.day.isoformat(),
                        "signal_observed_date": previous_session.day.isoformat(),
                        "action": "buy",
                        "ticker": ticker,
                        "execution_price": as_float(price_bar.close),
                        "quantity": as_float(quantity),
                        "usd_amount": as_float(purchase_value),
                        "realized_gain_loss": None,
                        "target_weight_pct": as_float(Decimal(str(order["target_weight"])) * 100),
                        "model_score": holding.get("model_score", 0),
                        "entry_signal": holding.get("entry_signal"),
                        "reason": "new model position" if Decimal(str(holding["initial_cost"])) == purchase_value else "rebalance band",
                    }
                )

        total_traded += traded_today
        equity = cash
        sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        signal_counts: defaultdict[str, int] = defaultdict(int)
        for ticker, holding in holdings.items():
            price_bar = on_or_before(charts[ticker], session)
            if not price_bar:
                continue
            peak_price = max(Decimal(str(holding.get("peak_price") or price_bar.close)), price_bar.close)
            last_close = Decimal(str(holding.get("last_close") or price_bar.close))
            daily_move = pct_change(price_bar.close, last_close) if last_close else Decimal("0")
            if daily_move < 0:
                adverse_moves = list(holding.get("daily_adverse_moves_pct", []))
                adverse_moves.append(as_float(daily_move))
                holding["daily_adverse_moves_pct"] = adverse_moves[-20:]
            holding["last_close"] = price_bar.close
            holding["peak_price"] = peak_price
            position_drawdown = pct_change(price_bar.close, peak_price)
            holding["max_position_drawdown_pct"] = min(
                Decimal(str(holding.get("max_position_drawdown_pct", 0))),
                position_drawdown,
            )
            value = Decimal(str(holding["shares"])) * price_bar.close
            equity += value
            sector_values[str(holding.get("sector") or "Unclassified")] += value
            signal_counts[str(holding.get("entry_signal") or "unknown")] += 1
        series.append(
            {
                "date": session.isoformat(),
                "value": as_float(equity),
                "cash": as_float(cash),
                "invested_value": as_float(equity - cash),
                "active_positions": len(holdings),
            }
        )
        daily_rebalances.append(
            {
                "date": session.isoformat(),
                "signal_observed_date": previous_session.day.isoformat(),
                "buys": buys,
                "sells": sells,
                "traded_value": as_float(traded_today),
                "turnover_pct": as_float(pct_change(equity + traded_today, equity)) if equity else 0,
                "position_count": len(holdings),
                "cash_pct": as_float(cash / equity * 100) if equity else 0,
            }
        )
        sector_exposure.append(
            {
                "date": session.isoformat(),
                "sectors": [
                    {
                        "sector": sector,
                        "value": as_float(value),
                        "weight_pct": as_float(value / equity * 100) if equity else 0,
                    }
                    for sector, value in sorted(sector_values.items(), key=lambda item: item[1], reverse=True)
                ],
            }
        )
        signal_mix.append(
            {
                "date": session.isoformat(),
                "signals": [
                    {
                        "signal": signal,
                        "positions": count,
                        "weight_pct": as_float(Decimal(count) / Decimal(len(holdings)) * 100) if holdings else 0,
                    }
                    for signal, count in sorted(signal_counts.items())
                ],
            }
        )
        previous_session = on_or_before(market_bars, session)

    final_equity = Decimal(str(series[-1]["value"]))
    positions: list[dict[str, object]] = []
    for ticker, holding in holdings.items():
        price_bar = on_or_before(charts[ticker], latest_market.day)
        if not price_bar:
            continue
        current_value = Decimal(str(holding["shares"])) * price_bar.close
        remaining_cost = Decimal(str(holding["remaining_cost"]))
        positions.append(
            {
                "ticker": ticker,
                "sector": holding.get("sector"),
                "entry_signal": holding.get("entry_signal"),
                "entry_date": holding.get("entry_date"),
                "shares": as_float(Decimal(str(holding["shares"]))),
                "average_cost": as_float(Decimal(str(holding["average_cost"]))),
                "latest_price": as_float(price_bar.close),
                "current_value": as_float(current_value),
                "portfolio_weight_pct": as_float(current_value / final_equity * 100) if final_equity else 0,
                "gain_loss": as_float(current_value - remaining_cost),
                "return_pct": as_float(pct_change(current_value, remaining_cost)),
                "model_score": holding.get("model_score", 0),
                "signal_score": holding.get("signal_score", 0),
                "news_articles_7d": holding.get("news_articles_7d", 0),
                "peak_price": as_float(Decimal(str(holding.get("peak_price", price_bar.close)))),
                "current_drawdown_pct": as_float(
                    pct_change(price_bar.close, Decimal(str(holding.get("peak_price", price_bar.close))))
                ),
                "max_position_drawdown_pct": as_float(Decimal(str(holding.get("max_position_drawdown_pct", 0)))),
                "drawdown_control_reason": holding.get("drawdown_control_reason"),
                "drawdown_control_observed_date": holding.get("drawdown_control_observed_date"),
                "average_daily_drawdown_pct": as_float(_average_daily_drawdown_pct(holding)),
                "average_drawdown_sell_point_pct": as_float(
                    _average_drawdown_sell_point_pct(holding, intraday_proxy=risk_mode == "v4")
                ),
                "status": "open",
            }
        )
    positions.sort(key=lambda row: row["portfolio_weight_pct"], reverse=True)

    latest_selected, latest_weights = portfolio_targets(latest_market.day, holdings, update_streaks=False)
    latest_by_ticker = {str(row["ticker"]): row for row in latest_selected}
    macro_context = bank_of_canada_macro_context(latest_market.day)
    macro_multiplier = Decimal(str(macro_context.get("equity_exposure_multiplier") or 1))
    pending_orders: list[dict[str, object]] = []
    for ticker in sorted(set(holdings) | set(latest_weights)):
        price_bar = on_or_before(charts[ticker], latest_market.day)
        if not price_bar:
            continue
        current_value = Decimal(str(holdings.get(ticker, {}).get("shares", 0))) * price_bar.close
        target_weight = latest_weights.get(ticker, Decimal("0"))
        target_value = final_equity * target_weight
        delta = target_value - current_value
        if target_weight and ticker in holdings and final_equity and abs(delta) / final_equity < MODEL_REBALANCE_BAND:
            continue
        if abs(delta) < Decimal("1"):
            continue
        candidate = latest_by_ticker.get(ticker, {})
        pending_orders.append(
            {
                "date": "next available close",
                "signal_observed_date": latest_market.day.isoformat(),
                "action": "buy" if delta > 0 else "sell",
                "ticker": ticker,
                "usd_amount": as_float(abs(delta)),
                "macro_adjusted_usd_amount": as_float(abs(delta) * macro_multiplier),
                "macro_exposure_multiplier": as_float(macro_multiplier),
                "target_weight_pct": as_float(target_weight * 100),
                "entry_signal": candidate.get("entry_signal") or holdings.get(ticker, {}).get("entry_signal"),
                "model_score": as_float(Decimal(str(candidate.get("model_score", 0)))) if candidate else None,
                "reason": holdings.get(ticker, {}).get("drawdown_control_reason")
                or ("new model position" if ticker not in holdings else "removed from model" if not target_weight else "rebalance band"),
                "status": "pending",
            }
        )

    benchmark = benchmark_comparison(series)
    closed_returns = [Decimal(str(row["return_pct"])) for row in realized_positions]
    top_five_weight = sum((Decimal(str(row["portfolio_weight_pct"])) for row in positions[:5]), Decimal("0"))
    latest_sectors = sector_exposure[-1]["sectors"] if sector_exposure else []
    return {
        "portfolio_name": portfolio_name,
        "from_date": VARIABLE_STRATEGY_START.isoformat(),
        "to_date": latest_market.day.isoformat(),
        "initial_value": as_float(MODEL_INITIAL_CAPITAL),
        "current_value": as_float(final_equity),
        "gain_loss": as_float(final_equity - MODEL_INITIAL_CAPITAL),
        "return_pct": as_float(pct_change(final_equity, MODEL_INITIAL_CAPITAL)),
        **fixed_changes_from_series(series),
        "cash": as_float(cash),
        "cash_pct": as_float(cash / final_equity * 100) if final_equity else 0,
        "position_count": len(positions),
        "positions": positions,
        "realized_positions": sorted(realized_positions, key=lambda row: row["return_pct"], reverse=True),
        "trade_ledger": trade_ledger,
        "pending_next_close_orders": pending_orders,
        "daily_rebalances": daily_rebalances,
        "series": series,
        "sector_exposure": sector_exposure,
        "signal_mix": signal_mix,
        "benchmark_comparison": benchmark,
        "macro_context": {
            **macro_context,
            "portfolio_use": (
                "Shown as a current macro overlay for all model portfolios. Historical trades stay "
                "point-in-time; pending next-close orders include a suggested macro-adjusted dollar amount, "
                "while base portfolio return statistics remain pre-overlay."
            ),
        },
        "statistics": {
            "total_trades": len(trade_ledger),
            "total_turnover_pct": as_float(total_traded / MODEL_INITIAL_CAPITAL * 100),
            "closed_positions": len(realized_positions),
            "closed_win_rate_pct": as_float(
                Decimal(sum(value > 0 for value in closed_returns)) / Decimal(len(closed_returns)) * 100
            ) if closed_returns else 0,
            "median_closed_return_pct": as_float(Decimal(str(median(closed_returns)))) if closed_returns else 0,
            "top_five_weight_pct": as_float(top_five_weight),
            "sector_count": len(latest_sectors),
            "largest_sector_weight_pct": max((row["weight_pct"] for row in latest_sectors), default=0),
            "available_universe_count": len(charts),
            "drawdown_control_actions": sum(
                1
                for row in trade_ledger
                if "drawdown" in str(row.get("reason") or "").casefold()
            ),
            "open_positions_under_8pct_drawdown": sum(
                1
                for row in positions
                if Decimal(str(row.get("current_drawdown_pct", 0))) <= MODEL_V2_SOFT_DRAWDOWN
            ),
            "average_drawdown_sell_point_count": sum(
                1
                for row in trade_ledger
                if "sell point" in str(row.get("reason") or "").casefold()
            ),
        },
        "methodology": {
            "initial_capital": as_float(MODEL_INITIAL_CAPITAL),
            "invested_target_pct": as_float(MODEL_INVESTED_TARGET * 100),
            "maximum_positions": MODEL_MAX_POSITIONS,
            "maximum_name_weight_pct": as_float(MODEL_MAX_NAME_WEIGHT * 100),
            "maximum_sector_weight_pct": as_float(MODEL_MAX_SECTOR_WEIGHT * 100),
            "maximum_names_per_sector": MODEL_MAX_NAMES_PER_SECTOR,
            "rebalance_band_pct": as_float(MODEL_REBALANCE_BAND * 100),
            "minimum_model_score": as_float(MODEL_MIN_SCORE),
            "near_signal_minimum_score": as_float(MODEL_NEAR_MIN_SCORE),
            "exit_buffer_sessions": MODEL_EXIT_BUFFER_SESSIONS,
            "execution_convention": "Observe only information available through one market close; execute generated dollar orders at the next available close.",
            "universe_convention": "Stocks become eligible no earlier than asset_universe.added_at and require strategy_eligible=true.",
            "macro_overlay": (
                "Official Bank of Canada RSS feeds are scored for easing, tightening, risk, and growth language. "
                "The latest dated context is included in each model response. Pending orders show a suggested "
                "macro-adjusted dollar amount, but historical returns remain base-model returns unless a future "
                "model explicitly applies the dated macro overlay during replay."
            ),
            "weighting": {
                "base": "Diversified score tilt: signal strength, relative strength, volume, trend confirmation, news activity, and volatility control.",
                "v2": "Model 2.0 starts with the same diversified score tilt, then reduces or exits holdings when position-level drawdown is not confirmed by fresh/strict signal, volume, one-month relative strength, and active or accelerating news.",
                "v3": "Model 3.0 starts with Model 2.0, then estimates each holding's sell point from its own trailing average negative daily moves and sells or trims at the next close when current drawdown breaches that point without confirmation.",
                "v4": "Model 4.0 starts with Model 3.0, then tightens sell points to approximate intraday stops using daily close data. This is a proxy until true intraday OHLC bars are available.",
            }.get(risk_mode, ""),
            "drawdown_overlay": None if risk_mode == "base" else {
                "soft_drawdown_pct": as_float(MODEL_V2_SOFT_DRAWDOWN),
                "medium_drawdown_pct": as_float(MODEL_V2_MEDIUM_DRAWDOWN),
                "hard_drawdown_pct": as_float(MODEL_V2_HARD_DRAWDOWN),
                "high_volatility_pct": as_float(MODEL_V2_HIGH_VOLATILITY),
                "average_daily_drawdown_multiplier": as_float(MODEL_V3_DRAWDOWN_MULTIPLIER),
                "minimum_average_drawdown_sell_point_pct": as_float(MODEL_V3_MIN_SELL_DRAWDOWN),
                "maximum_average_drawdown_sell_point_pct": as_float(MODEL_V3_MAX_SELL_DRAWDOWN),
                "intraday_proxy_multiplier": as_float(MODEL_V4_INTRADAY_PROXY_MULTIPLIER),
                "rule": {
                    "v2": "Soft drawdowns trim weak-volume/weak-relative-strength names; medium drawdowns cut exposure when confirmation weakens or news is inactive; hard drawdowns exit unless fresh/strict signals, volume, one-month relative strength, and news support remain intact.",
                    "v3": "Estimate a sell point from trailing average negative daily returns. If current drawdown breaches the sell point and confirmation is weak or news is inactive, sell at next close; if approaching the sell point, trim.",
                    "v4": "Use the same average-drawdown sell point but tighten it as an intraday-stop proxy. Daily close data means this is not true intraday execution.",
                }.get(risk_mode, ""),
            },
        },
        "news_counts_to_date": daily_news.get("to_date"),
        "warnings": [
            "The historical universe is reconstructed from asset_universe.added_at. It may still contain survivorship or data-entry bias if those dates do not reflect when an idea was actually known.",
            "No transaction costs, taxes, bid/ask spreads, or market-impact slippage are included.",
            *(
                [
                    "Model 2.0 drawdown controls are risk-management rules, not proof that drawdowns are predictable. They may reduce losses but can also sell before recoveries."
                ]
                if risk_mode in {"v2", "v3", "v4"}
                else []
            ),
            *(
                [
                    "Model 4.0 is an intraday proxy using daily close data. It does not yet use real intraday high/low bars, so stop timing is approximate."
                ]
                if risk_mode == "v4"
                else []
            ),
        ],
    }
