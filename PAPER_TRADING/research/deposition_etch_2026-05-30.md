# Deposition And Etch Sector Tracker

Recorded as trader name `deposition-etch`.

## Portfolio Convention

- Simulation date: May 20, 2026 close.
- Allocation: `$1,000` per recorded public company.
- Currency: USD-quoted symbols only, so the shared tracker can value every
  recorded position consistently.

## Recorded Positions

| Company | Tracker symbol | Exposure |
| --- | --- | --- |
| Applied Materials | `AMAT` | CVD, PVD, CMP, ion implantation, and broader wafer-fabrication tools |
| Lam Research | `LRCX` | Etch and deposition tools |
| Tokyo Electron | `TOELY` | CVD, coater/developer, and etch tools |
| ASM International | `ASMIY` | ALD tools, including PEALD and thermal ALD |
| Axcelis Technologies | `ACLS` | Ion implantation systems |

## Documented Without A Recorded Position

| Company | Reason |
| --- | --- |
| Kokusai Electric | Public Tokyo Stock Exchange listing `6525.T`, but the shared tracker does not yet support its JPY-denominated series |
| Mattson Technology | Private company since its 2016 acquisition by Beijing E-Town Dragon; dry strip, etch, and thermal-processing exposure |
| `VD` | Unresolved entry from the supplied list; no semiconductor-equipment company or usable tracker symbol was identified |

## Bottleneck Notes

The category tracks equipment used to deposit, modify, and remove thin films
during semiconductor fabrication. Node transitions and advanced packaging
increase the number and complexity of process steps, making tool qualification,
configuration, and capacity important constraints.

`TOELY` and `ASMIY` are USD-quoted OTC instruments. Their tracker prices are
useful for portfolio measurement, but lower OTC liquidity can differ from the
primary-market execution experience.

Kokusai Electric remains in the research map rather than being removed or
replaced with an unrelated proxy. Its native listing can be added once the
shared tracker supports JPY conversion.

Axcelis currently trades as `ACLS`. Axcelis and Veeco have announced a merger
that is expected to close in the second half of 2026, subject to the remaining
conditions. The combined company is expected to adopt a new name and ticker
after closing, so the tracker mapping will need to be reviewed if the merger
completes.

## Sources

- [Applied Materials investor relations](https://ir.appliedmaterials.com/)
- [Lam Research investor relations](https://investor.lamresearch.com/overview)
- [Lam Research at a glance](https://www.lamresearch.com/wp-content/uploads/2021/03/LRAG_English-A4-digital.pdf)
- [Tokyo Electron investor FAQ](https://www.tel.com/ir/faq/)
- [ASM share performance](https://www.asm.com/investors/share-performance)
- [Kokusai Electric investor relations](https://www.kokusai-electric.com/en/ir)
- [Axcelis investor relations](https://investor.axcelis.com/)
- [Axcelis first-quarter 2026 results and pending Veeco merger](https://investor.axcelis.com/news-releases/news-release-details/axcelis-announces-financial-results-first-quarter-2026)
- [Mattson acquisition completion](https://www.sec.gov/Archives/edgar/data/928421/000119312516586518/d194899dex991.htm)

## Price References

The recorded May 20, 2026 closes were retrieved from the
[Yahoo Finance](https://finance.yahoo.com/) public chart feed.
