from __future__ import annotations

import calendar
from datetime import datetime
from pathlib import Path

from rich.console import Console

from cce.models import PlanItem
from cce.utils import ensure_dir, load_client_config, write_json

ANGLES = [
    "myth vs fact",
    "what to expect",
    "safety & trust",
    "process clarity",
    "common mistakes",
    "reassurance",
]


def _platform_sequence(mix: dict[str, float], total: int) -> list[str]:
    if not mix:
        return ["instagram"] * total

    counts = {k: int(total * v) for k, v in mix.items()}
    assigned = sum(counts.values())
    platforms = sorted(mix.keys(), key=lambda x: mix[x], reverse=True)
    idx = 0
    while assigned < total:
        p = platforms[idx % len(platforms)]
        counts[p] += 1
        assigned += 1
        idx += 1

    seq: list[str] = []
    for platform in platforms:
        seq.extend([platform] * counts[platform])
    return seq[:total]


def run_plan(client_dir: Path, month: str, console: Console) -> None:
    try:
        dt = datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise ValueError("Month must be in YYYY-MM format") from exc

    client = load_client_config(client_dir / "client.yaml")

    days_in_month = calendar.monthrange(dt.year, dt.month)[1]
    total_posts = max(1, round(client.content_strategy.cadence.posts_per_week * days_in_month / 7))

    pillars = client.content_strategy.pillars
    services = client.services
    platforms = _platform_sequence(client.content_strategy.cadence.mix, total_posts)

    items: list[PlanItem] = []
    for i in range(total_posts):
        pillar = pillars[i % len(pillars)].name
        service = services[i % len(services)]
        platform = platforms[i % len(platforms)] if platforms else client.primary_platforms[0]
        angle = ANGLES[i % len(ANGLES)]
        target_length = "short" if platform in {"instagram", "tiktok"} else "medium"
        items.append(
            PlanItem(
                id=f"{dt.strftime('%Y%m')}-{i + 1:03d}",
                pillar=pillar,
                service=service,
                platform=platform,
                angle=angle,
                target_length=target_length,
            )
        )

    run_dir = ensure_dir(client_dir / "runs" / month)
    out_path = run_dir / "plan.json"
    write_json(out_path, {"month": month, "items": [item.model_dump() for item in items]})

    console.print(f"[green]Plan complete[/green]: {len(items)} posts for {month}")
    console.print(f"[cyan]Wrote[/cyan] {out_path}")
