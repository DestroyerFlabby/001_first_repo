from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT.parent / ".env"
SNAPSHOT_FILE = ROOT / "data" / "news_snapshots.json"
CACHE_TTL = timedelta(hours=6)
CACHE_VERSION = 1
NEWS_WINDOW = timedelta(days=15)
MAX_ARTICLES = 150
DISPLAY_ARTICLES = 15
DISPLAY_VIDEOS = 10
LOCK = Lock()


def load_dotenv() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def domain(url: str) -> str:
    return urlparse(url).netloc.casefold().removeprefix("www.")


def fetch_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> dict[str, object]:
    request = Request(
        url,
        headers={"User-Agent": "stock-tracking-advanced/1.0", **(headers or {})},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def alpaca_articles(ticker: str, now: datetime) -> tuple[list[dict[str, str]], dict[str, object]]:
    load_dotenv()
    api_key = os.environ.get("ALPACA_KEY") or os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("ALPACA_SECRET") or os.environ.get("APCA_API_SECRET_KEY")
    if not api_key or not api_secret:
        return [], {"source": "alpaca-news", "status": "unconfigured"}

    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
    }
    articles: list[dict[str, str]] = []
    next_page_token: str | None = None
    while len(articles) < MAX_ARTICLES:
        params = {
            "symbols": ticker,
            "start": (now - NEWS_WINDOW).isoformat(),
            "end": now.isoformat(),
            "limit": min(50, MAX_ARTICLES - len(articles)),
            "sort": "desc",
        }
        if next_page_token:
            params["page_token"] = next_page_token
        payload = fetch_json(
            f"https://data.alpaca.markets/v1beta1/news?{urlencode(params)}",
            headers,
        )
        batch = payload.get("news", [])
        if not isinstance(batch, list):
            break
        articles.extend(
            {
                "headline": str(row.get("headline", "")),
                "url": str(row.get("url", "")),
                "created_at": str(row.get("created_at", "")),
                "source": str(row.get("source", "alpaca-news")),
            }
            for row in batch
            if isinstance(row, dict) and row.get("url") and row.get("created_at")
        )
        next_page_token = str(payload.get("next_page_token") or "") or None
        if not next_page_token or not batch:
            break
    return articles, {
        "source": "alpaca-news",
        "status": "ok",
        "articles": len(articles),
        "truncated": bool(next_page_token),
    }


def gdelt_articles(ticker: str) -> tuple[list[dict[str, str]], dict[str, object]]:
    params = {
        "query": f'"{ticker} stock"',
        "mode": "artlist",
        "maxrecords": 100,
        "format": "json",
        "timespan": "15d",
    }
    payload = fetch_json(
        f"https://api.gdeltproject.org/api/v2/doc/doc?{urlencode(params)}",
        timeout=5,
    )
    rows = payload.get("articles", [])
    if not isinstance(rows, list):
        rows = []
    articles = [
        {
            "headline": str(row.get("title", "")),
            "url": str(row.get("url", "")),
            "created_at": datetime.strptime(
                str(row["seendate"]), "%Y%m%dT%H%M%SZ"
            ).replace(tzinfo=timezone.utc).isoformat(),
            "source": str(row.get("domain") or "gdelt"),
        }
        for row in rows
        if isinstance(row, dict) and row.get("url") and row.get("seendate")
    ]
    return articles, {
        "source": "gdelt-doc",
        "status": "ok",
        "articles": len(articles),
        "truncated": len(rows) >= 100,
    }


def youtube_videos(ticker: str, now: datetime) -> tuple[list[dict[str, str]], dict[str, object]]:
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return [], {"source": "youtube-data", "status": "unconfigured"}
    params = {
        "part": "snippet",
        "q": f"{ticker} stock",
        "type": "video",
        "order": "date",
        "publishedAfter": (now - NEWS_WINDOW).isoformat(),
        "maxResults": 50,
        "key": api_key,
    }
    payload = fetch_json(f"https://www.googleapis.com/youtube/v3/search?{urlencode(params)}")
    rows = payload.get("items", [])
    if not isinstance(rows, list):
        rows = []
    videos = [
        {
            "headline": str(row.get("snippet", {}).get("title", "")),
            "url": f"https://www.youtube.com/watch?v={row.get('id', {}).get('videoId')}",
            "created_at": str(row.get("snippet", {}).get("publishedAt", "")),
            "source": "youtube.com",
        }
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("id"), dict)
        and row["id"].get("videoId")
        and isinstance(row.get("snippet"), dict)
        and row["snippet"].get("publishedAt")
    ]
    return videos, {
        "source": "youtube-data",
        "status": "ok",
        "videos": len(videos),
        "truncated": bool(payload.get("nextPageToken")),
    }


def source_error(source: str, exc: Exception) -> dict[str, str]:
    if isinstance(exc, HTTPError):
        detail = f"HTTP {exc.code}"
    elif isinstance(exc, URLError):
        detail = str(exc.reason)
    else:
        detail = str(exc)
    return {"source": source, "status": "limited", "detail": detail}


def read_snapshots() -> dict[str, object]:
    if not SNAPSHOT_FILE.exists():
        return {"snapshots": {}}
    try:
        payload = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"snapshots": {}}
    return payload if isinstance(payload, dict) else {"snapshots": {}}


def write_snapshot(ticker: str, summary: dict[str, object]) -> None:
    with LOCK:
        payload = read_snapshots()
        snapshots = payload.setdefault("snapshots", {})
        if not isinstance(snapshots, dict):
            snapshots = {}
            payload["snapshots"] = snapshots
        ticker_rows = snapshots.setdefault(ticker, {})
        if not isinstance(ticker_rows, dict):
            ticker_rows = {}
            snapshots[ticker] = ticker_rows
        ticker_rows[str(summary["snapshot_date"])] = summary
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_FILE.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def cached_snapshot(ticker: str, now: datetime) -> dict[str, object] | None:
    snapshots = read_snapshots().get("snapshots", {})
    if not isinstance(snapshots, dict):
        return None
    ticker_rows = snapshots.get(ticker, {})
    if not isinstance(ticker_rows, dict):
        return None
    summary = ticker_rows.get(now.date().isoformat())
    if not isinstance(summary, dict):
        return None
    if summary.get("cache_version") != CACHE_VERSION:
        return None
    fetched_at = summary.get("fetched_at")
    if not isinstance(fetched_at, str):
        return None
    try:
        is_fresh = now - parse_timestamp(fetched_at) <= CACHE_TTL
    except ValueError:
        return None
    return summary if is_fresh else None


def summarize_articles(
    ticker: str,
    articles: list[dict[str, str]],
    videos: list[dict[str, str]],
    sources: list[dict[str, object]],
    now: datetime,
) -> dict[str, object]:
    deduped = {
        row["url"].casefold(): {
            **row,
            "domain": domain(row["url"]) or row["source"],
        }
        for row in articles
        if row.get("url") and row.get("created_at")
    }
    rows = sorted(
        deduped.values(),
        key=lambda row: parse_timestamp(row["created_at"]),
        reverse=True,
    )
    last_day = [row for row in rows if parse_timestamp(row["created_at"]) >= now - timedelta(days=1)]
    last_week = [row for row in rows if parse_timestamp(row["created_at"]) >= now - timedelta(days=7)]
    prior_week = [
        row
        for row in rows
        if now - timedelta(days=14) <= parse_timestamp(row["created_at"]) < now - timedelta(days=7)
    ]
    prior_daily_average = len(prior_week) / 7
    velocity = len(last_day) / prior_daily_average if prior_daily_average else None
    video_rows = sorted(
        videos,
        key=lambda row: parse_timestamp(row["created_at"]),
        reverse=True,
    )
    videos_last_week = [
        row for row in video_rows if parse_timestamp(row["created_at"]) >= now - timedelta(days=7)
    ]
    videos_prior_week = [
        row
        for row in video_rows
        if now - timedelta(days=14) <= parse_timestamp(row["created_at"]) < now - timedelta(days=7)
    ]
    video_velocity = (
        len(videos_last_week) / len(videos_prior_week) if videos_prior_week else None
    )
    return {
        "ticker": ticker,
        "cache_version": CACHE_VERSION,
        "snapshot_date": now.date().isoformat(),
        "fetched_at": now.isoformat(),
        "articles_24h": len(last_day),
        "articles_7d": len(last_week),
        "articles_prior_7d": len(prior_week),
        "daily_velocity_ratio": round(velocity, 4) if velocity is not None else None,
        "source_diversity_7d": len({row["domain"] for row in last_week}),
        "videos_7d": len(videos_last_week),
        "videos_prior_7d": len(videos_prior_week),
        "video_velocity_ratio": round(video_velocity, 4) if video_velocity is not None else None,
        "sources": sources,
        "articles": rows[:DISPLAY_ARTICLES],
        "videos": video_rows[:DISPLAY_VIDEOS],
        "note": (
            "News velocity compares the latest 24-hour article count with the "
            "daily average from the preceding seven days. Free sources can be "
            "incomplete or temporarily rate-limited."
        ),
    }


def news_summary(ticker: str) -> dict[str, object]:
    normalized = ticker.upper()
    now = utc_now()
    cached = cached_snapshot(normalized, now)
    if cached:
        return cached

    articles: list[dict[str, str]] = []
    videos: list[dict[str, str]] = []
    sources: list[dict[str, object]] = []
    try:
        rows, status = alpaca_articles(normalized, now)
        articles.extend(rows)
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("alpaca-news", exc))
    try:
        rows, status = gdelt_articles(normalized)
        articles.extend(rows)
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("gdelt-doc", exc))
    try:
        rows, status = youtube_videos(normalized, now)
        videos.extend(rows)
        sources.append(status)
    except Exception as exc:
        sources.append(source_error("youtube-data", exc))

    summary = summarize_articles(normalized, articles, videos, sources, now)
    try:
        write_snapshot(normalized, summary)
    except OSError:
        pass
    return summary
