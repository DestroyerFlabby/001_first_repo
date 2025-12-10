"""
Deterministic 48-month cashflow model matching the ChatGPT plan.

Usage:
    python PERSONAL_WEALTH_PLANNING/cashflow_model.py
This prints the monthly table and writes a CSV next to the script.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from dateutil.relativedelta import relativedelta
import csv


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
    expenses_monthly: dict
    lease: LeaseConfig
    mortgage: MortgageConfig

    @property
    def baseline_expenses_total(self) -> float:
        return float(sum(self.expenses_monthly.values()))


DEFAULT_CONFIG = ModelConfig(
    start_date=datetime(2025, 11, 1),
    months=48,
    income=IncomeConfig(
        nisarg_net_monthly_start=7200.0,
        sweta_net_monthly_start=5900.0,
        nisarg_bonus_net_dec=19100.0,
        sweta_bonus_net_dec=6500.0,
        annual_income_growth=0.01,
        combined_net_cap_annual=260000.0,
    ),
    expenses_monthly={
        "rent_or_mortgage_placeholder": 2950.0,
        "utilities": 80.0,
        "internet_phone": 50.0,
        "groceries": 1000.0,
        "dining_takeout": 1500.0,
        "entertainment_social": 700.0,
        "insurance_other": 100.0,
        "car_insurance": 390.0,
        "subscriptions": 18.0,
        "health_fitness": 150.0,
        "discretionary_misc": 650.0,
        "planned_savings": 2250.0,
    },
    lease=LeaseConfig(
        monthly_payment=776.0,
        security_deposit_month1=7500.0,
        start_month_index=1,
        term_months=48,
    ),
    mortgage=MortgageConfig(
        enable=True,
        start_month_index=15,
        p_and_i_monthly=4514.0,
        property_tax_monthly=708.0,
        home_insurance_monthly=100.0,
        rent_placeholder_monthly=2950.0,
    ),
)


def build_cashflow(config: ModelConfig = DEFAULT_CONFIG) -> List[dict]:
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


def _print_preview(rows: Iterable[dict], limit: int = 5) -> None:
    print(f"Generated {len(rows)} months.")
    print(f"First {limit} rows:")
    for row in list(rows)[:limit]:
        print(row)


if __name__ == "__main__":
    table = build_cashflow()
    csv_path = Path(__file__).with_suffix(".csv")
    _write_csv(table, csv_path)
    _print_preview(table)
    print(f"\nFull table saved to {csv_path}")
