from __future__ import annotations


WEALTHSIMPLE_FX_FEE_RATE = 0.015
OTC_VERIFY_SYMBOLS = {
    "AIQUY",
    "ASMIY",
    "CAJPY",
    "HOCPY",
    "KXIAY",
    "LYSCF",
    "MKKGY",
    "NINOY",
    "SHECY",
    "SIEGY",
    "SSLLF",
    "SUOPY",
    "TOELY",
    "UMICY",
}
CANADIAN_HEDGED_ALTERNATIVES = {
    "AAPL": "AAPL.TO",
    "AMD": "AMD.TO",
    "AMZN": "AMZN.TO",
    "AVGO": "AVGO.TO",
    "COST": "COST.TO",
    "GOOG": "GOOG.TO",
    "IBM": "IBM.TO",
    "META": "META.TO",
    "MSFT": "MSFT.TO",
    "NFLX": "NFLX.TO",
    "NVDA": "NVDA.TO",
    "VISA": "VISA.TO",
}


def wealthsimple_metadata(
    ticker: str,
    security_type: str,
    yahoo_symbol: str,
) -> dict[str, str | None]:
    alternative = CANADIAN_HEDGED_ALTERNATIVES.get(ticker)
    if security_type == "crypto":
        availability = "verify-in-app"
        reason = "Crypto availability is product-specific. Verify in Wealthsimple."
    elif yahoo_symbol.endswith(".TO") or yahoo_symbol.endswith(".V"):
        availability = "likely-supported"
        reason = "Canadian-listed security on a generally supported exchange. Verify in Wealthsimple."
    elif yahoo_symbol.endswith(".IL"):
        availability = "likely-unsupported"
        reason = "Non-North-American listing. Wealthsimple documents these as unsupported."
    elif ticker in OTC_VERIFY_SYMBOLS:
        availability = "verify-in-app"
        reason = "Possible OTC or ADR exposure. Wealthsimple supports only select OTC securities."
    else:
        availability = "likely-supported"
        reason = "Appears US-listed on a generally supported exchange. Liquidity and settlement rules still apply."
    return {
        "availability": availability,
        "reason": reason,
        "canadian_hedged_alternative": alternative,
        "alternative_note": (
            f"Reference CAD-hedged CDR: {alternative}. Verify current Wealthsimple availability."
            if alternative
            else None
        ),
    }
