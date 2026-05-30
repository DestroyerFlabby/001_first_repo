# CMP, Cleaning, And Metrology Sector Tracker

Recorded as trader name `cmp-cleaning-metrology`.

## Portfolio Convention

- Simulation date: May 20, 2026 close.
- Allocation: `$1,000` per recorded public company.
- Currency: USD-quoted symbols only, so the shared tracker can value every
  recorded position consistently.

## Recorded Positions

| Company | Tracker symbol | Exposure |
| --- | --- | --- |
| KLA | `KLAC` | Semiconductor inspection and metrology |
| Onto Innovation | `ONTO` | Overlay, optical, and film metrology |
| Entegris | `ENTG` | CMP slurries, pads, filters, and process materials |
| Qnity Electronics | `Q` | CMP pads, slurries, photoresists, and cleaning materials |
| Merck KGaA | `MKKGY` | Semiconductor materials, including planarization and photoresist exposure |

## Ownership And Mapping Notes

| Supplied company | Tracker treatment |
| --- | --- |
| CMC Materials | Acquired by Entegris in 2022; represented through `ENTG` |
| Cabot Microelectronics | Renamed CMC Materials before the Entegris acquisition; represented through `ENTG` |
| DuPont electronics materials | Spun out as Qnity Electronics in November 2025; represented directly through `Q`, not current DuPont ticker `DD` |
| JSR | Delisted in June 2024 and became private under Japan Investment Corporation control; documented without a recorded position |

## Bottleneck Notes

Chemical mechanical planarization depends on specialized pads, slurries,
filtration, and cleaning chemistries. As process complexity increases,
inspection and metrology tools are also required to detect yield loss and
control overlay and film properties.

This portfolio avoids double-counting CMC Materials and Cabot Microelectronics:
they are the same historical business lineage and are now included in Entegris.
It also uses Qnity for the former DuPont electronics-materials business because
that business is now independently listed.

`MKKGY` is a USD-quoted OTC ADR. Its tracker price is useful for portfolio
measurement, but OTC liquidity can differ from primary-market execution.

## Sources

- [KLA investor relations](https://ir.kla.com/)
- [Onto Innovation metrology purchase agreement](https://investors.ontoinnovation.com/news/news-details/2025/Onto-Innovation-Receives-Volume-Purchase-Agreement-from-a-Leading-DRAM-Manufacturer-for-Metrology-Product-Suite/default.aspx)
- [Entegris CMP solutions](https://www.entegris.com/en/home/our-science/by-industry/microelectronics/semiconductor/cmp.html)
- [Entegris acquisition of CMC Materials](https://investor.entegris.com/news/news-details/2022/Entegris-Completes-Acquisition-of-CMC-Materials-Solidifying-Position-as-the-Global-Leader-in-Electronic-Materials-07-06-2022/default.aspx)
- [Qnity semiconductor fabrication materials](https://www.qnityelectronics.com/semiconductor-fabrication-and-packaging-materials.html)
- [Qnity investor relations](https://ir.qnityelectronics.com/)
- [Merck KGaA electronics business](https://www.reports.emdgroup.com/en/annualreport/2023/management-report/fundamental-information-about-the-group/the-group/electronics.html)
- [JSR delisting announcement](https://www.jsr.co.jp/jsr_e/news/assets/pdf/20240624_01_e.pdf)

## Price References

The recorded May 20, 2026 closes were retrieved from the
[Yahoo Finance](https://finance.yahoo.com/) public chart feed.
