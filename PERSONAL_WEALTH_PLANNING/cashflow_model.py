"""
Deterministic 48-month cashflow model matching the ChatGPT plan.

Usage:
    python PERSONAL_WEALTH_PLANNING/cashflow_model.py --config cashflow_config.json
This prints the monthly table and writes a CSV next to the script unless an
explicit --output path is provided.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence

from dateutil.relativedelta import relativedelta


@dataclass(frozen=True)
class IncomeConfig:
    nisarg_net_monthly_start: float
    sweta_net_monthly_start: float
    nisarg_bonus_net_dec: float
    sweta_bonus_net_dec: float
    annual_income_growth: float
    combined_net_cap_annual: float

    @property
    def combined_net_cap_monthly(self) -> float:
        return self.combined_net_cap_annual / 12.0


@dataclass(frozen=True)
class LeaseConfig:
    monthly_payment: float
    security_deposit_month1: float
    start_month_index: int
    term_months: int


@dataclass(frozen=True)
class MortgageConfig:
    enable: bool
    start_month_index: int
    p_and_i_monthly: float
    property_tax_monthly: float
    home_insurance_monthly: float
    rent_placeholder_monthly: float

    @property
    def total_monthly(self) -> float:
        return (
            self.p_and_i_monthly
            + self.property_tax_monthly
            + self.home_insurance_monthly
        )

    @property
    def delta_vs_rent(self) -> float:
        return self.total_monthly - self.rent_placeholder_monthly


@dataclass(frozen=True)
class ModelConfig:
    start_date: datetime
    months: int
    income: IncomeConfig
    expenses_monthly: Mapping[str, float]
    lease: LeaseConfig
    mortgage: MortgageConfig

    @property
    def baseline_expenses_total(self) -> float:
        return float(sum(self.expenses_monthly.values()))


def load_config(config_path: Path) -> ModelConfig:
    """Load configuration values from a JSON file."""
    data = json.loads(config_path.read_text(encoding="utf-8"))
    start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
    income = IncomeConfig(**data["income"])
    lease = LeaseConfig(**data["lease"])
    mortgage = MortgageConfig(**data["mortgage"])
    expenses = {k: float(v) for k, v in data["expenses_monthly"].items()}
    return ModelConfig(
        start_date=start_date,
        months=int(data["months"]),
        income=income,
        expenses_monthly=expenses,
        lease=lease,
        mortgage=mortgage,
    )


def build_cashflow(config: ModelConfig) -> List[dict]:
    """Implement the month-by-month algorithm from the plan."""
    income_cfg = config.income
    lease_cfg = config.lease
    mortgage_cfg = config.mortgage

    nisarg = income_cfg.nisarg_net_monthly_start
    sweta = income_cfg.sweta_net_monthly_start
    cumulative = 0.0
    rows: List[dict] = []

    for idx in range(1, config.months + 1):
        current_date = config.start_date + relativedelta(months=idx - 1)

        # Growth 1% every 12-month cycle starting at Month 13.
        if idx > 12 and (idx - 1) % 12 == 0:
            nisarg *= 1 + income_cfg.annual_income_growth
            sweta *= 1 + income_cfg.annual_income_growth

        # Cap combined monthly income if it exceeds the threshold.
        combined = nisarg + sweta
        cap = income_cfg.combined_net_cap_monthly
        if combined > cap:
            scale = cap / combined
            nisarg *= scale
            sweta *= scale

        nisarg_bonus = income_cfg.nisarg_bonus_net_dec if current_date.month == 12 else 0.0
        sweta_bonus = income_cfg.sweta_bonus_net_dec if current_date.month == 12 else 0.0
        total_income = nisarg + sweta + nisarg_bonus + sweta_bonus

        expenses_total = config.baseline_expenses_total

        car_cf = 0.0
        if lease_cfg.start_month_index <= idx < lease_cfg.start_month_index + lease_cfg.term_months:
            car_cf -= lease_cfg.monthly_payment
        if idx == lease_cfg.start_month_index:
            car_cf -= lease_cfg.security_deposit_month1

        mortgage_adj = 0.0
        if mortgage_cfg.enable and idx >= mortgage_cfg.start_month_index:
            mortgage_adj -= mortgage_cfg.delta_vs_rent

        net_cf = total_income - expenses_total + car_cf + mortgage_adj
        cumulative += net_cf

        rows.append(
            {
                "Month": current_date.strftime("%b %Y"),
                "NisargIncome": round(nisarg, 2),
                "SwetaIncome": round(sweta, 2),
                "NisargBonus": round(nisarg_bonus, 2),
                "SwetaBonus": round(sweta_bonus, 2),
                "TotalIncome": round(total_income, 2),
                "ExpensesTotal": round(expenses_total, 2),
                "CarCashflow": round(car_cf, 2),
                "MortgageAdjustment": round(mortgage_adj, 2),
                "NetCashflow": round(net_cf, 2),
                "CumulativeSavings": round(cumulative, 2),
            }
        )

    return rows


def _write_csv(rows: Sequence[dict], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _print_preview(rows: Sequence[dict], limit: int = 5) -> None:
    print(f"Generated {len(rows)} months.")
    print(f"First {limit} rows:")
    for row in rows[:limit]:
        print(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the 48-month cashflow model.")
    default_config = Path(__file__).with_name("cashflow_config.json")
    default_output = Path(__file__).with_suffix(".csv")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config,
        help=f"Path to config JSON (default: {default_config.name})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"CSV path to write (default: {default_output.name})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    table = build_cashflow(config)
    _write_csv(table, args.output)
    _print_preview(table)
    print(f"\nFull table saved to {args.output.resolve()}")


if __name__ == "__main__":
    main()
