from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "research"


def slug_for(path: Path) -> str:
    return path.stem.lower().replace("_", "-")


def title_for(path: Path, content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").title()


def tags_for(path: Path, content: str) -> list[str]:
    text = f"{path.stem} {content[:1200]}".casefold()
    tags = []
    for tag, pattern in {
        "strategy": r"strategy|backtest|grid",
        "signals": r"signal|volume|fresh|strict|near",
        "news": r"news|catalyst|article",
        "sector": r"sector|semiconductor|infrastructure|memory|lithography|packaging",
        "watchlist": r"watchlist|candidate|mass.change",
    }.items():
        if re.search(pattern, text):
            tags.append(tag)
    return tags or ["research"]


def markdown_files() -> list[Path]:
    if not RESEARCH_DIR.exists():
        return []
    return sorted(RESEARCH_DIR.glob("*.md"), key=lambda path: path.name.casefold())


def research_index_response() -> dict[str, object]:
    notes = []
    for path in markdown_files():
        content = path.read_text(encoding="utf-8", errors="replace")
        notes.append(
            {
                "slug": slug_for(path),
                "title": title_for(path, content),
                "filename": path.name,
                "tags": tags_for(path, content),
                "size_bytes": path.stat().st_size,
            }
        )
    return {"notes": notes, "total": len(notes)}


def research_note_response(slug: str) -> dict[str, object]:
    normalized_slug = slug.casefold()
    for path in markdown_files():
        if slug_for(path) != normalized_slug:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        return {
            "slug": slug_for(path),
            "title": title_for(path, content),
            "filename": path.name,
            "tags": tags_for(path, content),
            "content": content,
        }
    raise KeyError(slug)
