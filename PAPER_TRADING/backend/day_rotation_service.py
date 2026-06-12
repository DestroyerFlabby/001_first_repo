from __future__ import annotations

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
    on_or_before,
    owners_by_asset,
    pct_change,
    sector_for_asset,
    yahoo_symbol,
)
from backend.model_portfolio_service import _asset_available, _asset_ever_available, _trailing_volatility
from backend.news_strategy import load_daily_news_counts, news_metrics
from backend.universe_service import read_asset_universe


ROTATION_PORTFOLIO_NAME = "daily-eod-rotation-portfolio"
ROTATION_INITIAL_CAPITAL = Decimal("100000")
ROTATION_INVESTED_TARGET = Decimal("0.95")
ROTATION_MAX_POSITIONS = 10
ROTATION_MAX_NAME_WEIGHT = Decimal("0.12")
ROTATION_MAX_SECTOR_WEIGHT = Decimal("0.30")
ROTATION_MAX_NAMES_PER_SECTOR = 3
ROTATION_REBALANCE_BAND = Decimal("0.015")
ROTATION_MIN_SCORE = Decimal("58")
ROTATION_NEAR_MIN_SCORE = Decimal("92")


def _horizon(signal: dict[str, object], key: str) -> dict[str, object]:
    horizons = signal.get("horizons", {}) if isinstance(signal.get("horizons"), dict) else {}
    value = horizons.get(key, {})
    return value if isinstance(value, dict) else {}


def _rotation_score(
    signal: dict[str, object],
    category: str,
    news: dict[str, Decimal | int | None],
    volatility_pct: Decimal,
) -> tuple[Decimal, dict[str, float]]:
    three_day = _horizon(signal, "3d")
    five_day = _horizon(signal, "5d")
    one_month = _horizon(signal, "1m")
    signal_score = Decimal(str(signal.get("overall_score", 0)))
    category_bonus = {"fresh": Decimal("30"), "strict": Decimal("16"), "near": Decimal("0")}.get(
        category, Decimal("0")
    )
    short_momentum = clamp(Decimal(str(three_day.get("return_pct", 0))), Decimal("-8"), Decimal("15")) * Decimal("0.8")
    short_momentum += clamp(Decimal(str(five_day.get("relative_strength_pct", 0))), Decimal("-8"), Decimal("18"))
    volume_ratio = Decimal(str(five_day.get("volume_ratio", 1)))
    volume_bonus = clamp((volume_ratio - Decimal("1")) * Decimal("15"), Decimal("-6"), Decimal("20"))
    news_bonus = Decimal("0")
    if int(news["articles_7d"]) > 0:
        news_bonus += Decimal("6")
    if int(news["articles_7d"]) > int(news["articles_prior_7d"]):
        news_bonus += Decimal("10")
    overextension_penalty = Decimal("0")
    if Decimal(str(three_day.get("return_pct", 0))) > Decimal("25"):
        overextension_penalty += Decimal("12")
    if Decimal(str(one_month.get("return_pct", 0))) > Decimal("80"):
        overextension_penalty += Decimal("12")
    volatility_penalty = clamp((volatility_pct - Decimal("65")) * Decimal("0.15"), Decimal("0"), Decimal("15"))
    score = signal_score + category_bonus + short_momentum + volume_bonus + news_bonus
    score -= overextension_penalty + volatility_penalty
    return score, {
        "signal_score": as_float(signal_score),
        "category_bonus": as_float(category_bonus),
        "short_momentum": as_float(short_momentum),
        "volume_bonus": as_float(volume_bonus),
        "news_bonus": as_float(news_bonus),
        "overextension_penalty": as_float(overextension_penalty),
        "volatility_penalty": as_float(volatility_penalty),
    }


def _select_rotation_candidates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked = sorted(rows, key=lambda row: (Decimal(str(row["rotation_score"])), str(row["ticker"])), reverse=True)
    selected: list[dict[str, object]] = []
    sector_counts: defaultdict[str, int] = defaultdict(int)
    for row in ranked:
        sector = str(row["sector"])
        if len(selected) >= ROTATION_MAX_POSITIONS:
            break
        if sector_counts[sector] >= ROTATION_MAX_NAMES_PER_SECTOR:
            continue
        selected.append(row)
        sector_counts[sector] += 1
    return selected


def _rotation_weights(rows: list[dict[str, object]]) -> dict[str, Decimal]:
    if not rows:
        return {}
    scores = [Decimal(str(row["rotation_score"])) for row in rows]
    floor = min(scores)
    raw = {str(row["ticker"]): Decimal("1") + (Decimal(str(row["rotation_score"])) - floor) / Decimal("100") for row in rows}
    total = sum(raw.values(), Decimal("0"))
    weights = {ticker: min(value / total * ROTATION_INVESTED_TARGET, ROTATION_MAX_NAME_WEIGHT) for ticker, value in raw.items()}
    sectors = {str(row["ticker"]): str(row["sector"]) for row in rows}
    sector_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for ticker, weight in weights.items():
        sector_totals[sectors[ticker]] += weight
    for sector, total_weight in sector_totals.items():
        if total_weight <= ROTATION_MAX_SECTOR_WEIGHT:
            continue
        scale = ROTATION_MAX_SECTOR_WEIGHT / total_weight
        for ticker in weights:
            if sectors[ticker] == sector:
                weights[ticker] *= scale
    return weights


def daily_rotation_portfolio_response(end: date | None = None) -> dict[str, object]:
    universe = read_asset_universe()
    owners = owners_by_asset()
    _, market_bars = fetch_chart("SPY")
    latest_market = on_or_before(market_bars, end)
    if not latest_market or latest_market.day < VARIABLE_STRATEGY_START:
        raise ValueError("daily rotation portfolio requires an ending market date on or after 2026-01-31")
    sessions = [bar.day for bar in market_bars if VARIABLE_STRATEGY_START <= bar.day <= latest_market.day]
    if not sessions:
        raise ValueError("missing daily rotation market sessions")

    charts: dict[str, tuple[object, ...]] = {}
    sectors: dict[str, str] = {}
    rows_by_ticker: dict[str, dict[str, object]] = {}
    for row in (item for item in universe if _asset_ever_available(item, latest_market.day)):
        ticker = str(row["ticker"])
        asset_type = str(row["asset_type"])
        try:
            _, bars = fetch_chart(yahoo_symbol(ticker, asset_type))
        except Exception:
            continue
        if not bars:
            continue
        charts[ticker] = bars
        rows_by_ticker[ticker] = row
        configured_sector = str(row.get("sector") or "").strip()
        sectors[ticker] = configured_sector or sector_for_asset(
            ticker, asset_type, owners.get((ticker, asset_type), [ROTATION_PORTFOLIO_NAME])
        )[0]

    daily_news = load_daily_news_counts()
    news_counts = daily_news.get("tickers", {})
    if not isinstance(news_counts, dict):
        news_counts = {}

    def candidates(observed_day: date) -> list[dict[str, object]]:
        candidates_for_day: list[dict[str, object]] = []
        for ticker, bars in charts.items():
            if not _asset_available(rows_by_ticker[ticker], observed_day):
                continue
            signal_bars = tuple(bar for bar in bars if bar.day <= observed_day)
            signal = live_signal(signal_bars)
            category = entry_signal(signal)
            if not category or not isinstance(signal, dict):
                continue
            counts = news_counts.get(ticker, {})
            news = news_metrics(counts if isinstance(counts, dict) else {}, observed_day)
            score, components = _rotation_score(signal, category, news, _trailing_volatility(signal_bars))
            minimum = ROTATION_NEAR_MIN_SCORE if category == "near" else ROTATION_MIN_SCORE
            if score < minimum:
                continue
            candidates_for_day.append({
                "ticker": ticker,
                "sector": sectors[ticker],
                "entry_signal": category,
                "rotation_score": score,
                "signal_score": signal.get("overall_score", 0),
                "news_articles_7d": int(news["articles_7d"]),
                "score_components": components,
            })
        return _select_rotation_candidates(candidates_for_day)

    cash = ROTATION_INITIAL_CAPITAL
    holdings: dict[str, dict[str, object]] = {}
    trades: list[dict[str, object]] = []
    realized: list[dict[str, object]] = []
    series: list[dict[str, object]] = []
    daily_rotations: list[dict[str, object]] = []
    sector_exposure: list[dict[str, object]] = []
    total_traded = Decimal("0")
    previous_session = on_or_before(market_bars, VARIABLE_STRATEGY_START - timedelta(days=1))

    for session in sessions:
        if not previous_session:
            previous_session = on_or_before(market_bars, session - timedelta(days=1))
        selected = candidates(previous_session.day)
        selected_by_ticker = {str(row["ticker"]): row for row in selected}
        weights = _rotation_weights(selected)
        observed_equity = cash
        observed_values: dict[str, Decimal] = {}
        for ticker, holding in holdings.items():
            bar = on_or_before(charts[ticker], previous_session.day)
            if bar:
                observed_values[ticker] = Decimal(str(holding["shares"])) * bar.close
                observed_equity += observed_values[ticker]

        orders: list[dict[str, object]] = []
        for ticker in sorted(set(holdings) | set(weights)):
            current_value = observed_values.get(ticker, Decimal("0"))
            target_weight = weights.get(ticker, Decimal("0"))
            delta = observed_equity * target_weight - current_value
            if target_weight and ticker in holdings and observed_equity and abs(delta) / observed_equity < ROTATION_REBALANCE_BAND:
                continue
            if abs(delta) >= Decimal("1"):
                orders.append({
                    "ticker": ticker,
                    "action": "buy" if delta > 0 else "sell",
                    "usd_amount": abs(delta),
                    "target_weight": target_weight,
                    "candidate": selected_by_ticker.get(ticker, {}),
                })

        buys = sells = 0
        traded_today = Decimal("0")
        for order in sorted(orders, key=lambda item: 0 if item["action"] == "sell" else 1):
            ticker = str(order["ticker"])
            bar = on_or_before(charts[ticker], session)
            if not bar or bar.day <= previous_session.day:
                continue
            target_weight = Decimal(str(order["target_weight"]))
            candidate = order["candidate"] if isinstance(order["candidate"], dict) else {}
            if order["action"] == "sell":
                holding = holdings.get(ticker)
                if not holding:
                    continue
                available_value = Decimal(str(holding["shares"])) * bar.close
                full_exit = target_weight == 0
                sale_value = available_value if full_exit else min(Decimal(str(order["usd_amount"])), available_value)
                quantity = Decimal(str(holding["shares"])) if full_exit else sale_value / bar.close
                cost = quantity * Decimal(str(holding["average_cost"]))
                pnl = sale_value - cost
                holding["shares"] = Decimal(str(holding["shares"])) - quantity
                holding["remaining_cost"] = Decimal(str(holding["remaining_cost"])) - cost
                holding["proceeds"] = Decimal(str(holding["proceeds"])) + sale_value
                holding["realized_pnl"] = Decimal(str(holding["realized_pnl"])) + pnl
                cash += sale_value
                sells += 1
                traded_today += sale_value
                trades.append({
                    "date": bar.day.isoformat(), "signal_observed_date": previous_session.day.isoformat(),
                    "action": "sell", "ticker": ticker, "entry_signal": holding.get("entry_signal"),
                    "rotation_score": holding.get("rotation_score"), "execution_price": as_float(bar.close),
                    "quantity": as_float(quantity), "usd_amount": as_float(sale_value),
                    "target_weight_pct": as_float(target_weight * 100), "realized_gain_loss": as_float(pnl),
                    "reason": "rotated out of daily top ranks" if full_exit else "daily target rebalance",
                })
                if full_exit:
                    realized.append({
                        "ticker": ticker, "entry_date": holding["entry_date"], "exit_date": bar.day.isoformat(),
                        "initial_value": as_float(Decimal(str(holding["initial_cost"]))),
                        "ending_value": as_float(Decimal(str(holding["proceeds"]))),
                        "gain_loss": as_float(Decimal(str(holding["realized_pnl"]))),
                        "return_pct": as_float(pct_change(Decimal(str(holding["proceeds"])), Decimal(str(holding["initial_cost"])))),
                        "entry_signal": holding.get("entry_signal"), "sector": holding.get("sector"), "status": "closed",
                    })
                    del holdings[ticker]
            else:
                purchase = min(Decimal(str(order["usd_amount"])), cash)
                if purchase < Decimal("1"):
                    continue
                quantity = purchase / bar.close
                holding = holdings.get(ticker)
                if holding:
                    old_shares = Decimal(str(holding["shares"]))
                    old_cost = Decimal(str(holding["remaining_cost"]))
                    holding["shares"] = old_shares + quantity
                    holding["remaining_cost"] = old_cost + purchase
                    holding["initial_cost"] = Decimal(str(holding["initial_cost"])) + purchase
                    holding["average_cost"] = (old_cost + purchase) / (old_shares + quantity)
                else:
                    holding = holdings[ticker] = {
                        "shares": quantity, "average_cost": bar.close, "remaining_cost": purchase,
                        "initial_cost": purchase, "proceeds": Decimal("0"), "realized_pnl": Decimal("0"),
                        "entry_date": bar.day.isoformat(), "sector": candidate.get("sector", sectors[ticker]),
                    }
                holding.update({
                    "entry_signal": candidate.get("entry_signal", holding.get("entry_signal")),
                    "rotation_score": as_float(Decimal(str(candidate.get("rotation_score", 0)))),
                    "signal_score": candidate.get("signal_score", 0), "news_articles_7d": candidate.get("news_articles_7d", 0),
                })
                cash -= purchase
                buys += 1
                traded_today += purchase
                trades.append({
                    "date": bar.day.isoformat(), "signal_observed_date": previous_session.day.isoformat(),
                    "action": "buy", "ticker": ticker, "entry_signal": holding.get("entry_signal"),
                    "rotation_score": holding.get("rotation_score"), "execution_price": as_float(bar.close),
                    "quantity": as_float(quantity), "usd_amount": as_float(purchase),
                    "target_weight_pct": as_float(target_weight * 100), "realized_gain_loss": None,
                    "reason": "entered daily top ranks" if Decimal(str(holding["initial_cost"])) == purchase else "daily target rebalance",
                })

        total_traded += traded_today
        equity = cash
        sector_values: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for ticker, holding in holdings.items():
            bar = on_or_before(charts[ticker], session)
            if bar:
                value = Decimal(str(holding["shares"])) * bar.close
                equity += value
                sector_values[str(holding.get("sector") or "Unclassified")] += value
        series.append({
            "date": session.isoformat(), "value": as_float(equity), "cash": as_float(cash),
            "invested_value": as_float(equity - cash), "active_positions": len(holdings),
        })
        daily_rotations.append({
            "date": session.isoformat(), "signal_observed_date": previous_session.day.isoformat(),
            "buys": buys, "sells": sells, "traded_value": as_float(traded_today),
            "turnover_pct": as_float(traded_today / equity * 100) if equity else 0,
            "position_count": len(holdings), "cash_pct": as_float(cash / equity * 100) if equity else 0,
        })
        sector_exposure.append({
            "date": session.isoformat(),
            "sectors": [
                {"sector": sector, "value": as_float(value), "weight_pct": as_float(value / equity * 100) if equity else 0}
                for sector, value in sorted(sector_values.items(), key=lambda item: item[1], reverse=True)
            ],
        })
        previous_session = on_or_before(market_bars, session)

    final_equity = Decimal(str(series[-1]["value"]))
    positions: list[dict[str, object]] = []
    for ticker, holding in holdings.items():
        bar = on_or_before(charts[ticker], latest_market.day)
        if not bar:
            continue
        value = Decimal(str(holding["shares"])) * bar.close
        cost = Decimal(str(holding["remaining_cost"]))
        positions.append({
            "ticker": ticker, "sector": holding.get("sector"), "entry_signal": holding.get("entry_signal"),
            "entry_date": holding.get("entry_date"), "shares": as_float(Decimal(str(holding["shares"]))),
            "average_cost": as_float(Decimal(str(holding["average_cost"]))), "latest_price": as_float(bar.close),
            "current_value": as_float(value), "portfolio_weight_pct": as_float(value / final_equity * 100) if final_equity else 0,
            "gain_loss": as_float(value - cost), "return_pct": as_float(pct_change(value, cost)),
            "rotation_score": holding.get("rotation_score", 0), "signal_score": holding.get("signal_score", 0),
            "news_articles_7d": holding.get("news_articles_7d", 0), "status": "open",
        })
    positions.sort(key=lambda row: row["portfolio_weight_pct"], reverse=True)

    latest_selected = candidates(latest_market.day)
    latest_weights = _rotation_weights(latest_selected)
    latest_by_ticker = {str(row["ticker"]): row for row in latest_selected}
    pending: list[dict[str, object]] = []
    for ticker in sorted(set(holdings) | set(latest_weights)):
        bar = on_or_before(charts[ticker], latest_market.day)
        if not bar:
            continue
        current = Decimal(str(holdings.get(ticker, {}).get("shares", 0))) * bar.close
        target_weight = latest_weights.get(ticker, Decimal("0"))
        delta = final_equity * target_weight - current
        if target_weight and ticker in holdings and final_equity and abs(delta) / final_equity < ROTATION_REBALANCE_BAND:
            continue
        if abs(delta) < Decimal("1"):
            continue
        candidate = latest_by_ticker.get(ticker, {})
        pending.append({
            "date": "next available close", "signal_observed_date": latest_market.day.isoformat(),
            "action": "buy" if delta > 0 else "sell", "ticker": ticker, "usd_amount": as_float(abs(delta)),
            "target_weight_pct": as_float(target_weight * 100),
            "entry_signal": candidate.get("entry_signal") or holdings.get(ticker, {}).get("entry_signal"),
            "rotation_score": as_float(Decimal(str(candidate.get("rotation_score", 0)))) if candidate else None,
            "reason": "entered daily top ranks" if ticker not in holdings else "rotated out of daily top ranks" if not target_weight else "daily target rebalance",
            "status": "pending",
        })

    benchmark = benchmark_comparison(series)
    closed_returns = [Decimal(str(row["return_pct"])) for row in realized]
    latest_sectors = sector_exposure[-1]["sectors"] if sector_exposure else []
    return {
        "portfolio_name": ROTATION_PORTFOLIO_NAME,
        "from_date": VARIABLE_STRATEGY_START.isoformat(), "to_date": latest_market.day.isoformat(),
        "initial_value": as_float(ROTATION_INITIAL_CAPITAL), "current_value": as_float(final_equity),
        "gain_loss": as_float(final_equity - ROTATION_INITIAL_CAPITAL),
        "return_pct": as_float(pct_change(final_equity, ROTATION_INITIAL_CAPITAL)),
        **fixed_changes_from_series(series),
        "cash": as_float(cash), "cash_pct": as_float(cash / final_equity * 100) if final_equity else 0,
        "position_count": len(positions), "positions": positions,
        "realized_positions": sorted(realized, key=lambda row: row["return_pct"], reverse=True),
        "trade_ledger": trades, "pending_next_close_orders": pending,
        "daily_rebalances": daily_rotations, "series": series, "sector_exposure": sector_exposure,
        "benchmark_comparison": benchmark,
        "statistics": {
            "total_trades": len(trades), "total_turnover_pct": as_float(total_traded / ROTATION_INITIAL_CAPITAL * 100),
            "closed_positions": len(realized),
            "closed_win_rate_pct": as_float(Decimal(sum(value > 0 for value in closed_returns)) / Decimal(len(closed_returns)) * 100) if closed_returns else 0,
            "median_closed_return_pct": as_float(Decimal(str(median(closed_returns)))) if closed_returns else 0,
            "top_five_weight_pct": as_float(sum((Decimal(str(row["portfolio_weight_pct"])) for row in positions[:5]), Decimal("0"))),
            "sector_count": len(latest_sectors), "largest_sector_weight_pct": max((row["weight_pct"] for row in latest_sectors), default=0),
            "available_universe_count": len(charts),
        },
        "methodology": {
            "initial_capital": as_float(ROTATION_INITIAL_CAPITAL), "invested_target_pct": as_float(ROTATION_INVESTED_TARGET * 100),
            "maximum_positions": ROTATION_MAX_POSITIONS, "maximum_name_weight_pct": as_float(ROTATION_MAX_NAME_WEIGHT * 100),
            "maximum_sector_weight_pct": as_float(ROTATION_MAX_SECTOR_WEIGHT * 100),
            "maximum_names_per_sector": ROTATION_MAX_NAMES_PER_SECTOR,
            "rebalance_band_pct": as_float(ROTATION_REBALANCE_BAND * 100),
            "minimum_rotation_score": as_float(ROTATION_MIN_SCORE), "near_signal_minimum_score": as_float(ROTATION_NEAR_MIN_SCORE),
            "execution_convention": "Observe close-based signals and news through one market close; execute generated orders at the next available close.",
            "universe_convention": "Stocks become eligible no earlier than asset_universe.added_at and require strategy_eligible=true.",
            "weighting": "Daily EOD rotation toward the highest-ranked fresh, strict, and exceptional near signals using short momentum, relative strength, volume, news acceleration, overextension, and volatility controls.",
        },
        "warnings": [
            "This is a daily EOD rotation simulation, not an intraday day-trading backtest. Daily bars cannot model intraday signal timing or fills.",
            "High turnover makes the result especially sensitive to bid/ask spreads, slippage, taxes, and market impact, none of which are included.",
            "The point-in-time universe depends on asset_universe.added_at and may retain survivorship or data-entry bias.",
        ],
    }
