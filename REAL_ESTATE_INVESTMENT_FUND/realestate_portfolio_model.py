"""
Build a 5-year Ontario real-estate fund model driven by external market stats.

Outputs:
  - REAL_ESTATE_INVESTMENT_FUND/RealEstate_Portfolio_5yr_Conservative.xlsx
  - REAL_ESTATE_INVESTMENT_FUND/RealEstate_Portfolio_5yr_Expanded.xlsx

Both workbooks contain property-level underwriting tables; the expanded
version adds the LP/GP waterfall tab and cites the external sources.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np
import numpy_financial as npf
import pandas as pd


@dataclass
class PropertyPlan:
    city: str
    property_type: str
    count: int
    units_per_property: int
    price_multiplier: float
    rent_unit_type: str
    role: str


def mortgage_payment(principal: float, annual_rate: float, amort_years: int) -> float:
    """Monthly mortgage payment."""
    monthly_rate = annual_rate / 12
    n = amort_years * 12
    if monthly_rate == 0:
        return principal / n
    factor = (1 + monthly_rate) ** n
    return principal * (monthly_rate * factor) / (factor - 1)


def remaining_balance(
    principal: float, payment: float, annual_rate: float, payments_made: int, amort_years: int
) -> float:
    """Outstanding balance after a number of monthly payments."""
    monthly_rate = annual_rate / 12
    n = amort_years * 12
    if monthly_rate == 0:
        return principal - payment * payments_made
    factor = (1 + monthly_rate) ** n
    paid_factor = (1 + monthly_rate) ** payments_made
    return principal * (factor - paid_factor) / (factor - 1)


def irr(values: Sequence[float]) -> float | None:
    try:
        return float(npf.irr(values))
    except (FloatingPointError, ValueError, ZeroDivisionError):
        return None


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def build_property_projection(
    plan: PropertyPlan,
    market: dict,
    assumptions: dict,
) -> dict:
    avg_price = market["avg_price"]
    rent_stats = market["rent_stats"]
    rent_monthly_per_unit = rent_stats[plan.rent_unit_type]
    purchase_price = avg_price * plan.price_multiplier
    equity_per_property = purchase_price * (1 - assumptions["ltv"])
    loan_amount = purchase_price - equity_per_property
    payment = mortgage_payment(loan_amount, assumptions["interest_rate_mid"], assumptions["amortization_years"])
    annual_debt_service = payment * 12
    hold_years = assumptions["hold_years"]

    annual_cashflows: List[float] = []
    annual_noi: List[float] = []
    rent_growth = assumptions["rent_growth"]
    vacancy_rate = assumptions["vacancy_rate"]
    maintenance_rate = assumptions["maintenance_rate"]
    management_rate = assumptions["management_rate"]
    insurance_rate = assumptions["insurance_rate"]
    expense_growth = assumptions["expense_growth"]
    price_appreciation = assumptions["price_appreciation"]

    for year in range(1, hold_years + 1):
        rent_annual = rent_monthly_per_unit * plan.units_per_property * 12 * ((1 + rent_growth) ** (year - 1))
        vacancy = rent_annual * vacancy_rate
        maintenance = rent_annual * maintenance_rate
        management = rent_annual * management_rate
        insurance = purchase_price * insurance_rate * ((1 + expense_growth) ** (year - 1))
        noi = rent_annual - vacancy - maintenance - management - insurance
        cashflow = noi - annual_debt_service
        annual_noi.append(noi)
        annual_cashflows.append(cashflow)

    # Add sale proceeds to year 5 cashflow.
    value_year5 = purchase_price * ((1 + price_appreciation) ** hold_years)
    remaining = remaining_balance(
        loan_amount,
        payment,
        assumptions["interest_rate_mid"],
        hold_years * 12,
        assumptions["amortization_years"],
    )
    net_sale = value_year5 * (1 - assumptions["disposition_cost_rate"]) - remaining
    annual_cashflows[-1] += net_sale

    return {
        "plan": plan,
        "purchase_price": purchase_price,
        "equity_per_property": equity_per_property,
        "loan_amount": loan_amount,
        "annual_cashflows": annual_cashflows,
        "annual_noi": annual_noi,
        "annual_debt_service": annual_debt_service,
        "rent_monthly_per_unit": rent_monthly_per_unit,
        "market_sources": {
            "price": market["avg_price_source"],
            "rent": market["rent_source"],
        },
    }


def aggregate_portfolio(projections: List[dict], assumptions: dict) -> dict:
    hold_years = assumptions["hold_years"]
    total_equity = 0.0
    total_cost = 0.0
    annual_totals = [0.0] * hold_years
    property_rows = []

    for proj in projections:
        plan = proj["plan"]
        count = plan.count
        total_equity += proj["equity_per_property"] * count
        total_cost += proj["purchase_price"] * count
        for idx, cf in enumerate(proj["annual_cashflows"]):
            annual_totals[idx] += cf * count
        property_rows.append(
            {
                "City": plan.city,
                "PropertyType": plan.property_type,
                "Role": plan.role,
                "Count": count,
                "PurchasePrice_perProperty": round(proj["purchase_price"], 0),
                "TotalPurchase": round(proj["purchase_price"] * count, 0),
                "Equity_perProperty": round(proj["equity_per_property"], 0),
                "Year1_NOI_perProperty": round(proj["annual_noi"][0], 0),
                "Year1_Cashflow_perProperty": round(proj["annual_cashflows"][0], 0),
                "MonthlyRent_perUnit": round(proj["rent_monthly_per_unit"], 0),
            }
        )

    management_fee = total_equity * assumptions["gp_management_fee_rate"]
    annual_after_fees = [cf - management_fee for cf in annual_totals]

    return {
        "total_equity": total_equity,
        "total_cost": total_cost,
        "annual_totals": annual_totals,
        "management_fee": management_fee,
        "annual_after_fees": annual_after_fees,
        "property_rows": property_rows,
    }


def run_waterfall(
    net_cashflows: Sequence[float],
    total_equity: float,
    pref_rate: float,
    promote: float,
) -> List[dict]:
    lp_pref_due = 0.0
    lp_pref_paid = 0.0
    lp_capital_returned = 0.0
    gp_catchup_paid = 0.0
    capital_balance = total_equity
    results = []

    for year, cash in enumerate(net_cashflows, start=1):
        lp_dist = 0.0
        gp_dist = 0.0

        lp_pref_due += capital_balance * pref_rate
        pay_pref = min(cash, lp_pref_due)
        lp_pref_paid += pay_pref
        lp_pref_due -= pay_pref
        cash -= pay_pref
        lp_dist += pay_pref

        pay_capital = min(cash, capital_balance)
        lp_capital_returned += pay_capital
        capital_balance -= pay_capital
        cash -= pay_capital
        lp_dist += pay_capital

        target_gp = (promote / (1 - promote)) * (lp_pref_paid + lp_capital_returned)
        catchup_needed = max(0.0, target_gp - gp_catchup_paid)
        catchup_paid = min(cash, catchup_needed)
        gp_catchup_paid += catchup_paid
        cash -= catchup_paid
        gp_dist += catchup_paid

        if cash > 0:
            gp_dist += cash * promote
            lp_dist += cash * (1 - promote)
            cash = 0.0

        results.append(
            {
                "Year": year,
                "LP_Distribution": lp_dist,
                "GP_Distribution": gp_dist,
                "LP_Pref_Balance": lp_pref_due,
                "Capital_Balance": capital_balance,
            }
        )

    return results


def write_workbook(base_path: Path, filename: str, sheets: Dict[str, pd.DataFrame]) -> None:
    target = base_path / filename
    with pd.ExcelWriter(target, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)


def build_sources_table(market_stats: dict) -> pd.DataFrame:
    rows = []
    for city, stats in market_stats.items():
        rows.append(
            {
                "City": city,
                "AveragePriceSource": stats["avg_price_source"],
                "RentSource": stats["rent_source"],
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ontario real-estate fund financial model")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("portfolio_config.json"),
        help="Path to portfolio_config.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory to store Excel outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    assumptions = config["assumptions"]

    plans = [
        PropertyPlan(
            city=item["city"],
            property_type=item["property_type"],
            count=item["count"],
            units_per_property=item["units_per_property"],
            price_multiplier=item["price_multiplier"],
            rent_unit_type=item["rent_unit_type"],
            role=item["role"],
        )
        for item in config["portfolio"]
    ]

    projections = [
        build_property_projection(plan, config["market_stats"][plan.city], assumptions) for plan in plans
    ]
    portfolio = aggregate_portfolio(projections, assumptions)

    net_cashflows = portfolio["annual_after_fees"]
    total_equity = portfolio["total_equity"]
    cashflows_with_investment = [-total_equity] + net_cashflows
    gross_irr = irr(cashflows_with_investment)
    gross_multiple = (sum(cf for cf in net_cashflows if cf > 0) / total_equity) if total_equity else None

    waterfall_rows = run_waterfall(
        net_cashflows,
        total_equity,
        assumptions["preferred_return"],
        assumptions["promote"],
    )

    lp_cashflows = [-total_equity]
    gp_cashflows = [0.0]
    for idx, row in enumerate(waterfall_rows):
        lp_cashflows.append(row["LP_Distribution"])
        gp_cashflows.append(portfolio["management_fee"] + row["GP_Distribution"])
        # management fee reduces LP distributable cash so it is already excluded from waterfall inputs

    lp_irr = irr(lp_cashflows)
    lp_multiple = (sum(cf for cf in lp_cashflows[1:] if cf > 0) / total_equity) if total_equity else None
    gp_total = sum(gp_cashflows[1:])

    property_df = pd.DataFrame(portfolio["property_rows"])
    cashflow_df = pd.DataFrame(
        {
            "Year": list(range(1, assumptions["hold_years"] + 1)),
            "OperatingCF": [round(x, 0) for x in portfolio["annual_totals"]],
            "GP_Fee": [round(portfolio["management_fee"], 0)] * assumptions["hold_years"],
            "NetToEquity": [round(x, 0) for x in net_cashflows],
        }
    )
    waterfall_df = pd.DataFrame(waterfall_rows)
    summary_df = pd.DataFrame(
        [
            {"Metric": "Total Cost", "Value": round(portfolio["total_cost"], 0)},
            {"Metric": "Total Equity", "Value": round(total_equity, 0)},
            {"Metric": "Gross IRR", "Value": gross_irr},
            {"Metric": "Gross Equity Multiple", "Value": gross_multiple},
            {"Metric": "LP IRR", "Value": lp_irr},
            {"Metric": "LP Equity Multiple", "Value": lp_multiple},
            {"Metric": "GP Total Fees & Promote", "Value": gp_total},
        ]
    )

    output_dir = args.output_dir
    conservative_file = "RealEstate_Portfolio_5yr_Conservative.xlsx"
    expanded_file = "RealEstate_Portfolio_5yr_Expanded.xlsx"

    write_workbook(
        output_dir,
        conservative_file,
        {
            "PropertyMix": property_df,
            "Cashflows": cashflow_df,
            "Summary": summary_df,
        },
    )
    write_workbook(
        output_dir,
        expanded_file,
        {
            "PropertyMix": property_df,
            "Cashflows": cashflow_df,
            "Summary": summary_df,
            "Waterfall": waterfall_df,
            "Sources": build_sources_table(config["market_stats"]),
        },
    )

    print("Generated workbooks:")
    print(output_dir / conservative_file)
    print(output_dir / expanded_file)
    if gross_irr is not None:
        print(f"Gross IRR: {gross_irr:.2%}")
    if lp_irr is not None:
        print(f"LP IRR: {lp_irr:.2%}")
    print(f"GP total fees/promote over hold: ${gp_total:,.0f}")


if __name__ == "__main__":
    main()
