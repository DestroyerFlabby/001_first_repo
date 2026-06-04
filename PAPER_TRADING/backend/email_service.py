from __future__ import annotations

import json
import os
import smtplib
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.dashboard_cache import cached_or_build_eod, cached_or_build_overview
from backend.dashboard_service import trader_detail
from backend.news_service import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
EMAIL_LOG_FILE = ROOT / "data" / "email_notification_log.json"
LOG_LOCK = Lock()
DEFAULT_STRATEGY = "watchlist-variable-news-optimized-experimental"
DEFAULT_RECIPIENT = "nisargdave@hotmail.com"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def money(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def pct(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return str(value)


def number(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def line_items(rows: list[dict[str, Any]], formatter) -> list[str]:
    if not rows:
        return ["  None."]
    return [formatter(row) for row in rows]


def format_order(row: dict[str, Any]) -> str:
    action = str(row.get("action", "")).upper()
    ticker = row.get("ticker", "-")
    signal = row.get("entry_signal", "-")
    observed = row.get("signal_observed_date", "-")
    amount = money(row.get("usd_amount")) if row.get("action") == "buy" else "full position"
    quantity = number(row.get("quantity"))
    quantity_text = "" if row.get("action") == "buy" else f" | qty {quantity}"
    return f"  {action} {ticker} | signal {signal} | observed {observed} | amount {amount}{quantity_text}"


def format_holding(row: dict[str, Any]) -> str:
    return (
        f"  HOLD {row.get('ticker', '-')} | entry {row.get('entry_date', '-')} "
        f"({row.get('entry_signal', '-')}) | value {money(row.get('current_value'))} | "
        f"P/L {money(row.get('gain_loss'))} ({pct(row.get('return_pct'))}) | "
        f"daily {pct(row.get('daily_change_pct'))}, 5D {pct(row.get('five_day_change_pct'))}, "
        f"monthly {pct(row.get('monthly_change_pct'))}"
    )


def format_realized(row: dict[str, Any]) -> str:
    return (
        f"  SOLD {row.get('ticker', '-')} | {row.get('entry_date', '-')} to {row.get('exit_date', '-')} | "
        f"P/L {money(row.get('gain_loss'))} ({pct(row.get('return_pct'))})"
    )


def format_trader(row: dict[str, Any]) -> str:
    return (
        f"  #{row.get('rank', '-')} {row.get('investor', '-')} | "
        f"value {money(row.get('current_value'))} | P/L {money(row.get('gain_loss'))} | "
        f"return {pct(row.get('return_pct'))} | daily {pct(row.get('daily_change_pct'))}, "
        f"5D {pct(row.get('five_day_change_pct'))}, monthly {pct(row.get('monthly_change_pct'))} | "
        f"positions {row.get('position_count', '-')}"
    )


def stock_signal_label(row: dict[str, Any]) -> str:
    signal = row.get("signal")
    if not isinstance(signal, dict):
        return "-"
    classification = "fresh" if signal.get("fresh_priority") else signal.get("classification", "-")
    score = signal.get("overall_score")
    return f"{classification} {number(score)}/100"


def format_stock(row: dict[str, Any]) -> str:
    owners = ", ".join(str(owner) for owner in row.get("owners", []))
    return (
        f"  {row.get('ticker', '-')} | return {pct(row.get('return_pct'))} | "
        f"sector {row.get('sector', '-')} | "
        f"daily {pct(row.get('daily_change_pct'))}, 5D {pct(row.get('five_day_change_pct'))}, "
        f"monthly {pct(row.get('monthly_change_pct'))} | signal {stock_signal_label(row)} | "
        f"owners {owners or '-'}"
    )


def format_sector(row: dict[str, Any]) -> str:
    signals = row.get("signal_counts") if isinstance(row.get("signal_counts"), dict) else {}
    return (
        f"  #{row.get('rank', '-')} {row.get('sector', '-')} | "
        f"companies {row.get('instrument_count', '-')} | win {pct(row.get('win_rate_pct'))} | "
        f"avg {pct(row.get('average_return_pct'))} | median {pct(row.get('median_return_pct'))} | "
        f"daily {pct(row.get('daily_change_pct'))}, 5D {pct(row.get('five_day_change_pct'))}, "
        f"monthly {pct(row.get('monthly_change_pct'))} | "
        f"signals F {signals.get('fresh', 0)} / S {signals.get('strict', 0)} / "
        f"N {signals.get('near', 0)} / none {signals.get('none', 0)} | "
        f"top {row.get('top_ticker', '-')} {pct(row.get('top_return_pct'))} | "
        f"worst {row.get('bottom_ticker', '-')} {pct(row.get('bottom_return_pct'))}"
    )


def format_eod_trader(row: dict[str, Any]) -> str:
    return (
        f"  {row.get('investor', '-')} | daily return {pct(row.get('return_pct'))} | "
        f"P/L {money(row.get('gain_loss'))}"
    )


def format_eod_stock(row: dict[str, Any]) -> str:
    owners = ", ".join(str(owner) for owner in row.get("owners", []))
    return f"  {row.get('ticker', '-')} | daily return {pct(row.get('return_pct'))} | owners {owners or '-'}"


def parse_iso_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def trade_cutoff(detail: dict[str, Any], lookback_days: int = 5) -> date | None:
    to_date = parse_iso_date(detail.get("to_date"))
    if not to_date:
        return None
    return to_date - timedelta(days=lookback_days)


def recent_trades(detail: dict[str, Any]) -> list[dict[str, Any]]:
    cutoff = trade_cutoff(detail)
    if not cutoff:
        return []
    rows: list[dict[str, Any]] = []
    for trade in detail.get("simulated_trades") or []:
        trade_date = parse_iso_date(trade.get("date"))
        if trade_date and trade_date >= cutoff:
            rows.append(dict(trade))
    rows.sort(key=lambda row: (str(row.get("date", "")), str(row.get("ticker", "")), str(row.get("action", ""))))
    return rows


def format_recent_trade(row: dict[str, Any]) -> str:
    action = str(row.get("action", "")).upper()
    amount = money(row.get("usd_amount")) if row.get("usd_amount") is not None else "full position"
    gain_loss = "" if row.get("gain_loss") is None else f" | realized P/L {money(row.get('gain_loss'))}"
    return (
        f"  {row.get('date', '-')} | {action} {row.get('ticker', '-')} | "
        f"signal {row.get('entry_signal', '-')} | price {money(row.get('execution_price'))} | "
        f"qty {number(row.get('quantity'))} | amount {amount}{gain_loss}"
    )


def holdings_by_five_day(detail: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in detail.get("positions") or []]
    rows.sort(key=lambda row: abs(float(row.get("five_day_change_pct") or 0)), reverse=True)
    return rows


def dashboard_report_lines(overview: dict[str, Any], eod: dict[str, Any]) -> list[str]:
    traders = list(overview.get("traders") or [])
    stocks = sorted(
        (dict(row) for row in overview.get("stocks") or [] if not row.get("warning")),
        key=lambda row: float(row.get("return_pct") or 0),
        reverse=True,
    )
    metrics = overview.get("dashboard_metrics") or {}
    signal_mix = metrics.get("signal_mix") if isinstance(metrics, dict) else {}
    portfolio_breadth = metrics.get("portfolio_breadth") if isinstance(metrics, dict) else {}
    stock_breadth = metrics.get("stock_breadth") if isinstance(metrics, dict) else {}
    availability = overview.get("wealthsimple_availability") or {}
    sectors = list(overview.get("sector_breakdowns") or [])
    eod_traders = list(eod.get("traders") or [])
    eod_stocks = list(eod.get("stocks") or [])
    top_eod_stocks = eod_stocks[:5]
    bottom_eod_stocks = list(reversed(eod_stocks[-5:]))

    return [
        "Full dashboard report",
        f"Window: {overview.get('from_date')} to {overview.get('latest_available_date') or overview.get('to_date')}",
        f"Portfolios: {len(traders)}",
        f"Tracked instruments: {len(stocks)}",
        (
            "Signal mix: "
            f"fresh {signal_mix.get('fresh', '-')}, strict {signal_mix.get('strict', '-')}, "
            f"near {signal_mix.get('near', '-')}, none {signal_mix.get('none', '-')}"
            if isinstance(signal_mix, dict)
            else "Signal mix: -"
        ),
        (
            "Breadth: "
            f"portfolios positive {portfolio_breadth.get('positive_count', '-')} / "
            f"stocks positive {stock_breadth.get('positive_count', '-')}"
            if isinstance(portfolio_breadth, dict) and isinstance(stock_breadth, dict)
            else "Breadth: -"
        ),
        (
            "Wealthsimple estimate: "
            f"{availability.get('likely-supported', 0)} likely supported, "
            f"{availability.get('verify-in-app', 0)} verify in app, "
            f"{availability.get('likely-unsupported', 0)} likely unsupported"
        ),
        "",
        "Portfolio rankings",
        *line_items(traders, format_trader),
        "",
        "Sector breakdown",
        *line_items(sectors, format_sector),
        "",
        "Tracked instruments by selected-window return",
        *line_items(stocks, format_stock),
        "",
        f"Daily EOD portfolio movers: {eod.get('from_date')} to {eod.get('to_date')}",
        *line_items(eod_traders, format_eod_trader),
        "",
        "Top daily stock movers",
        *line_items(top_eod_stocks, format_eod_stock),
        "",
        "Bottom daily stock movers",
        *line_items(bottom_eod_stocks, format_eod_stock),
    ]


def portfolio_activity_lines(detail: dict[str, Any]) -> list[str]:
    pending = list(detail.get("pending_next_close_orders") or [])
    holdings = holdings_by_five_day(detail)
    trades = recent_trades(detail)
    realized = list(detail.get("realized_positions") or [])[:15]

    return [
        f"Focused portfolio activity: {detail.get('investor', DEFAULT_STRATEGY)}",
        f"Window: {detail.get('from_date')} to {detail.get('to_date')}",
        "",
        str(detail.get("execution_convention") or "Signals are observed after close and executed at the next available close."),
        "",
        "Changes made in the last 5 days",
        *line_items(trades, format_recent_trade),
        "",
        "Changes needed today / next available close",
        *line_items(pending, format_order),
        "",
        "Current holdings ranked by absolute 5D move",
        *line_items(holdings, format_holding),
        "",
        "Recently realized positions",
        *line_items(realized, format_realized),
        "",
        "Portfolio summary",
        f"  Current value: {money(detail.get('current_value'))}",
        f"  Gain / loss: {money(detail.get('gain_loss'))}",
        f"  Return: {pct(detail.get('return_pct'))}",
        f"  Daily: {pct(detail.get('daily_change_pct'))}",
        f"  5D: {pct(detail.get('five_day_change_pct'))}",
        f"  Monthly: {pct(detail.get('monthly_change_pct'))}",
    ]


def build_daily_report_body(
    overview: dict[str, Any],
    detail: dict[str, Any],
    eod: dict[str, Any],
) -> str:
    lines = [
        "Paper Trading Dashboard Daily Report",
        f"Generated: {datetime.now(notification_timezone()).isoformat(timespec='seconds')}",
        "",
        *dashboard_report_lines(overview, eod),
        "",
        "-" * 72,
        "",
        *portfolio_activity_lines(detail),
        "",
        "Generated by the Paper Trading Dashboard refresh.",
    ]
    return "\n".join(lines)


def notification_timezone() -> timezone | ZoneInfo:
    name = os.environ.get("DAILY_INSTRUCTIONS_TIMEZONE", "America/Toronto").strip()
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return timezone.utc


def today_key() -> str:
    return datetime.now(notification_timezone()).date().isoformat()


def log_key(day: str, recipient: str, strategy: str) -> str:
    return f"{day}|{recipient.casefold()}|{strategy.casefold()}"


def load_email_log() -> dict[str, Any]:
    if not EMAIL_LOG_FILE.exists():
        return {"sent": {}}
    try:
        payload = json.loads(EMAIL_LOG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"sent": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("sent"), dict):
        return {"sent": {}}
    return payload


def sent_record(day: str, recipient: str, strategy: str) -> dict[str, Any] | None:
    with LOG_LOCK:
        payload = load_email_log()
        record = payload["sent"].get(log_key(day, recipient, strategy))
        return record if isinstance(record, dict) else None


def mark_sent(day: str, recipient: str, strategy: str, metadata: dict[str, object]) -> None:
    with LOG_LOCK:
        payload = load_email_log()
        payload["sent"][log_key(day, recipient, strategy)] = {
            **metadata,
            "notification_date": day,
            "recipient": recipient,
            "strategy": strategy,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        EMAIL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        EMAIL_LOG_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def smtp_configured() -> tuple[bool, dict[str, str]]:
    load_dotenv()
    config = {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": os.environ.get("SMTP_PORT", "587").strip(),
        "username": os.environ.get("SMTP_USERNAME", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", "").strip(),
        "from_email": (
            os.environ.get("EMAIL_FROM", "").strip()
            or os.environ.get("SMTP_USERNAME", "").strip()
        ),
        "recipient": (
            os.environ.get("DAILY_INSTRUCTIONS_RECIPIENT", "").strip()
            or DEFAULT_RECIPIENT
        ),
        "strategy": (
            os.environ.get("DAILY_INSTRUCTIONS_STRATEGY", "").strip()
            or DEFAULT_STRATEGY
        ),
    }
    required = ("host", "port", "username", "password", "from_email", "recipient")
    return all(config[name] for name in required), config


def send_daily_instructions(
    start: date,
    end: date | None,
    apply_wealthsimple_fx_fees: bool = False,
) -> dict[str, object]:
    load_dotenv()
    if not env_bool("DAILY_INSTRUCTIONS_EMAIL_ENABLED"):
        return {
            "status": "skipped",
            "reason": "DAILY_INSTRUCTIONS_EMAIL_ENABLED is not true",
            "recipient": DEFAULT_RECIPIENT,
            "strategy": DEFAULT_STRATEGY,
        }

    configured, config = smtp_configured()
    notification_date = today_key()
    existing = sent_record(notification_date, config["recipient"], config["strategy"])
    if existing:
        return {
            "status": "skipped",
            "reason": f"daily dashboard report already sent on {notification_date}",
            "recipient": config["recipient"],
            "strategy": config["strategy"],
            "sent_at": existing.get("sent_at"),
        }

    if not configured:
        return {
            "status": "skipped",
            "reason": "SMTP settings are incomplete",
            "recipient": config["recipient"],
            "strategy": config["strategy"],
        }

    detail = trader_detail(
        config["strategy"],
        start,
        end,
        apply_wealthsimple_fx_fees=apply_wealthsimple_fx_fees,
    )
    overview = cached_or_build_overview(start, end, apply_wealthsimple_fx_fees)
    eod = cached_or_build_eod(apply_wealthsimple_fx_fees)
    message = EmailMessage()
    message["Subject"] = f"Daily dashboard report: {config['strategy']} as of {detail.get('to_date')}"
    message["From"] = config["from_email"]
    message["To"] = config["recipient"]
    message.set_content(build_daily_report_body(overview, detail, eod))

    try:
        port = int(config["port"])
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be a number") from exc

    timeout = int(os.environ.get("SMTP_TIMEOUT_SECONDS", "20"))
    with smtplib.SMTP(config["host"], port, timeout=timeout) as smtp:
        if env_bool("SMTP_USE_TLS", default=True):
            smtp.starttls()
        smtp.login(config["username"], config["password"])
        smtp.send_message(message)

    metadata = {
        "to_date": detail.get("to_date"),
        "pending_orders": len(detail.get("pending_next_close_orders") or []),
        "holdings": len(detail.get("positions") or []),
        "recent_trades": len(recent_trades(detail)),
    }
    mark_sent(notification_date, config["recipient"], config["strategy"], metadata)

    return {
        "status": "sent",
        "recipient": config["recipient"],
        "strategy": config["strategy"],
        **metadata,
    }
