# Advanced Packaging Sector Tracker

Recorded as trader name `advanced-packaging`.

## Portfolio Convention

- Simulation date: May 20, 2026 close.
- Allocation: `$1,000` per recorded public company.
- Currency: USD-quoted symbols only, so the shared tracker can value every
  recorded position consistently.

## Recorded Positions

| Company | Tracker symbol | Exposure |
| --- | --- | --- |
| TSMC | `TSM` | CoWoS, SoIC, and advanced packaging capacity |
| Samsung Electronics | `SMSN.IL` | HBM and advanced packaging |
| Micron Technology | `MU` | HBM3E and advanced memory |
| ASE Technology Holding | `ASX` | Major outsourced semiconductor assembly and test provider |
| Amkor Technology | `AMKR` | Outsourced semiconductor packaging and test, including advanced packaging |
| Intel | `INTC` | Indirect Intel Foundry packaging exposure, including EMIB and Foveros |

## Documented Without A Recorded Position

| Company | Reason |
| --- | --- |
| SK hynix | Core HBM supplier listed in Korea as `000660.KS`; pursuing a U.S. ADR listing in 2026, but no reliable USD tracker series is active yet |
| Brewer Science | Private company; temporary wafer bonding and debonding materials exposure |

## Bottleneck Notes

AI accelerators combine compute dies with stacked high-bandwidth memory using
advanced packaging. The tracked constraints therefore span:

- Foundry packaging capacity, including TSMC CoWoS and SoIC.
- HBM supply from Samsung and Micron, with SK hynix documented as a major
  unrecorded supplier until a USD tracker series is available.
- Outsourced packaging and test capacity from ASE and Amkor.
- Alternative advanced packaging paths from Intel Foundry, including EMIB and
  Foveros.
- Temporary wafer bonding materials from private supplier Brewer Science.

`SMSN.IL` is Samsung Electronics' USD-denominated London GDR. `INTC` represents
Intel as a whole rather than a pure-play Intel Foundry packaging return.

## Sources

- [TSMC fundamentals](https://investor.tsmc.com/english/fundamentals)
- [TSMC 2023 annual report: CoWoS and SoIC](https://investor.tsmc.com/static/annualReports/2023/english/index.html)
- [Samsung investor relations](https://www.samsung.com/global/ir/)
- [Micron investor relations](https://investors.micron.com/)
- [ASE advanced packaging announcement](https://www.aseglobal.com/press-room/310x310)
- [Amkor investor relations](https://ir.amkor.com/)
- [Intel Foundry packaging](https://www.intel.com/content/www/us/en/foundry/packaging.html)
- [Brewer Science packaging solutions](https://www.brewerscience.com/products/advanced-packaging/)
- [SK hynix company site](https://www.skhynix.com/)

## Price References

The recorded May 20, 2026 closes were retrieved from the
[Yahoo Finance](https://finance.yahoo.com/) public chart feed.
