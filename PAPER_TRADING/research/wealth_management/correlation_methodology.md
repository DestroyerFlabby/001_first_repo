# Correlation And Direct-Overlap Methodology

Date: 2026-06-12
Calculation version: `correlation-overlap-1.0`

## Purpose

The service tests whether the largest positions in one tracked portfolio have historically moved together and measures direct ticker overlap between two portfolios. It is research analytics, not a forecast or suitability determination.

## Correlation

- Select at most the 12 largest positive current positions by market value.
- Load daily closes for the requested window.
- Convert each price series to close-to-close simple returns.
- Align each pair on dates present in both return series. Missing dates are not forward-filled or imputed.
- Require at least 20 aligned return observations by default.
- Pearson correlation is unavailable when either aligned series has zero variance.

The response includes every pair, observation counts, unavailable reasons, average valid-pair correlation, and the five highest and lowest valid pairs. A warning is raised when average correlation is at least 0.70 or at least half of valid pairs are 0.80 or higher.

Correlation measures historical linear co-movement. It can change sharply and does not prove protection in a market stress event.

## Direct Overlap

Positions are grouped by normalized ticker. For each shared ticker:

```text
shared contribution = min(weight in portfolio A, weight in portfolio B)
direct overlap = sum(shared contributions)
```

This reports the percentage of each portfolio directly represented by the same ticker at the smaller of the two weights. Duplicate ticker rows inside a portfolio are combined before weights are calculated.

ETF constituent look-through is explicitly unavailable. Two different ETFs may hold similar securities without appearing as direct overlap, and one shared ETF is counted only as the ETF ticker rather than its constituents.

## Performance

Limiting the interactive calculation to 12 positions caps pairwise work at 66 correlations. Market fetching is isolated behind an injectable loader so production can use existing cache infrastructure and tests can use deterministic local series.
