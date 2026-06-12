from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.basket_service import basket_performance, custom_basket_response  # noqa: E402
from backend.dashboard_cache import cached_or_build_overview  # noqa: E402
from backend.dashboard_service import latest_market_date  # noqa: E402
from backend.wealth_intelligence_service import wealth_intelligence_response  # noqa: E402
from backend.wealth_operations_service import wealth_operations_response  # noqa: E402


DEFAULT_START = date(2026, 1, 31)
OUTPUT_DIR = ROOT / "research" / "ai_wealth"


def parse_date(value: str | None, default: date | None = None) -> date | None:
    if not value:
        return default
    return date.fromisoformat(value)


def safe_filename(value: str) -> str:
    return "".join(character if character.isalnum() or character in "._-" else "-" for character in value).strip("-")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field, "")) for field in fields})


def csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return value


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def pct(value: object) -> str:
    if value is None or value == "":
        return "-"
    return f"{float(value):+.2f}%"


def model_basket_performances(
    model_baskets: list[dict[str, Any]],
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model in model_baskets:
        basket_id = str(model["basket_id"])
        try:
            performance = basket_performance(basket_id, start, end)
        except Exception as exc:
            rows.append(
                {
                    "basket_id": basket_id,
                    "name": model.get("name"),
                    "role": model.get("role"),
                    "status": model.get("status"),
                    "member_count": model.get("member_count"),
                    "return_pct": None,
                    "benchmark_return_pct": None,
                    "alpha_pct": None,
                    "warning": str(exc),
                }
            )
            continue
        rows.append(
            {
                "basket_id": basket_id,
                "name": model.get("name"),
                "role": model.get("role"),
                "status": model.get("status"),
                "member_count": model.get("member_count"),
                "return_pct": performance.get("return_pct"),
                "benchmark_return_pct": performance.get("benchmark_return_pct"),
                "alpha_pct": performance.get("alpha_pct"),
                "from_date": performance.get("from_date"),
                "to_date": performance.get("to_date"),
                "warning": "",
            }
        )
    return rows


def build_markdown_report(payload: dict[str, Any], basket_rows: list[dict[str, Any]]) -> str:
    readiness = payload["business_readiness"]
    positioning = payload["positioning"]
    top_candidates = payload["ai_signal_candidates"][:15]
    themes = payload["theme_opportunities"][:10]
    return "\n\n".join(
        [
            "# AI Wealth Intelligence Snapshot",
            f"Window: {payload['from_date']} to {payload.get('latest_available_date') or payload.get('to_date')}",
            "## Positioning",
            positioning["recommended_claim"],
            "## Business Readiness",
            markdown_table(
                ["Metric", "Value"],
                [
                    ["Score", f"{readiness['score']:.2f} / 100"],
                    ["Stage", readiness["stage"]],
                    ["Disclaimer", payload["disclaimer"]],
                ],
            ),
            "## Model Basket Performance",
            markdown_table(
                ["Basket", "Role", "Members", "Return", "Benchmark", "Alpha", "Warning"],
                [
                    [
                        row["name"],
                        row["role"],
                        row["member_count"],
                        pct(row["return_pct"]),
                        pct(row["benchmark_return_pct"]),
                        pct(row["alpha_pct"]),
                        row["warning"] or "-",
                    ]
                    for row in basket_rows
                ],
            ),
            "## Theme Opportunities",
            markdown_table(
                ["Theme", "Candidates", "Model", "High risk", "Avg score", "Top tickers"],
                [
                    [
                        row["theme"],
                        row["candidate_count"],
                        row["model_candidates"],
                        row["high_risk_count"],
                        row["average_score"],
                        ", ".join(row["top_tickers"]),
                    ]
                    for row in themes
                ],
            ),
            "## AI Signal Candidates",
            markdown_table(
                ["Ticker", "Sector", "Score", "Signal", "Risk", "Action", "5D", "Monthly", "Flags", "Drivers"],
                [
                    [
                        row["ticker"],
                        row["sector"],
                        row["score"],
                        row["signal"],
                        row["risk_bucket"],
                        row["suggested_action"],
                        pct(row["five_day_change_pct"]),
                        pct(row["monthly_change_pct"]),
                        "; ".join(row.get("data_quality_flags") or []) or "-",
                        "; ".join(row["drivers"]),
                    ]
                    for row in top_candidates
                ],
            ),
            "## Risk Controls",
            "\n".join(f"- {item}" for item in payload["risk_controls"]),
            "## Next Build Steps",
            "\n".join(f"- {item}" for item in payload["next_build_steps"]),
        ]
    ) + "\n"


def write_operations_outputs(
    output_dir: Path,
    stem: str,
    operations: dict[str, Any],
) -> dict[str, Path]:
    operations_json_path = output_dir / f"{stem}_operations.json"
    proposals_path = output_dir / f"{stem}_proposals.csv"
    review_path = output_dir / f"{stem}_review_queue.csv"
    commands_path = output_dir / f"{stem}_ai_commands.csv"
    write_json(operations_json_path, operations)
    proposal_rows = []
    for row in operations["proposal_matrix"]:
        proposal_rows.append(
            {
                "profile_id": row["profile"]["profile_id"],
                "profile_name": row["profile"]["profile_name"],
                "review_status": row["review_status"],
                "proposal_return_pct": row["proposal_return_pct"],
                "proposal_alpha_pct": row["proposal_alpha_pct"],
                "allocation_count": row["allocation_count"],
                "policy_warnings": row["policy_warnings"],
                "next_best_actions": row["next_best_actions"],
            }
        )
    write_csv(
        proposals_path,
        proposal_rows,
        [
            "profile_id",
            "profile_name",
            "review_status",
            "proposal_return_pct",
            "proposal_alpha_pct",
            "allocation_count",
            "policy_warnings",
            "next_best_actions",
        ],
    )
    write_csv(
        review_path,
        operations["advisor_review_queue"],
        ["priority", "task_type", "subject", "source", "detail"],
    )
    write_csv(
        commands_path,
        operations["ai_command_workbench"],
        [
            "command_id",
            "title",
            "category",
            "trigger",
            "required_context",
            "output_type",
            "guardrail",
            "generated_prompt",
            "execution_mode",
        ],
    )
    return {
        "operations_json": operations_json_path,
        "proposals_csv": proposals_path,
        "review_queue_csv": review_path,
        "ai_commands_csv": commands_path,
    }


def generate_snapshot(start: date, end: date, output_dir: Path, apply_fees: bool = False) -> dict[str, Path]:
    overview = cached_or_build_overview(start, end, apply_fees)
    baskets = custom_basket_response(include_archived=False)
    payload = wealth_intelligence_response(overview, baskets, start, end)
    effective_end = date.fromisoformat(str(payload.get("latest_available_date") or end.isoformat()))
    basket_rows = model_basket_performances(payload["model_baskets"], start, effective_end)
    payload["model_basket_performance"] = basket_rows
    operations = wealth_operations_response(payload, start, effective_end)

    stem = safe_filename(f"ai_wealth_snapshot_{start.isoformat()}_to_{effective_end.isoformat()}")
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    candidates_path = output_dir / f"{stem}_candidates.csv"
    baskets_path = output_dir / f"{stem}_model_baskets.csv"

    write_json(json_path, payload)
    md_path.write_text(build_markdown_report(payload, basket_rows), encoding="utf-8")
    write_csv(
        candidates_path,
        payload["ai_signal_candidates"],
        [
            "ticker",
            "security_type",
            "sector",
            "score",
            "signal",
            "risk_bucket",
            "suggested_action",
            "return_pct",
            "daily_change_pct",
            "five_day_change_pct",
            "monthly_change_pct",
            "data_quality_flags",
            "drivers",
        ],
    )
    write_csv(
        baskets_path,
        basket_rows,
        [
            "basket_id",
            "name",
            "role",
            "status",
            "member_count",
            "return_pct",
            "benchmark_return_pct",
            "alpha_pct",
            "from_date",
            "to_date",
            "warning",
        ],
    )
    operation_paths = write_operations_outputs(output_dir, stem, operations)
    return {
        "json": json_path,
        "markdown": md_path,
        "candidates_csv": candidates_path,
        "model_baskets_csv": baskets_path,
        **operation_paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AI Wealth snapshots and model-basket reports.")
    parser.add_argument("--from-date", default=DEFAULT_START.isoformat())
    parser.add_argument("--to-date", default="", help="Defaults to latest available market close.")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--wealthsimple-fx-fees", action="store_true")
    args = parser.parse_args()

    start = parse_date(args.from_date, DEFAULT_START)
    end = parse_date(args.to_date) or latest_market_date()
    if start is None:
        raise ValueError("from-date is required")
    if end < start:
        raise ValueError("to-date must be on or after from-date")

    paths = generate_snapshot(
        start,
        end,
        Path(args.output_dir),
        apply_fees=args.wealthsimple_fx_fees,
    )
    for label, path in paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
