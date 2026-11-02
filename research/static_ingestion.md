# Non-time observation ingestion

MOF source: Jimenez Lopez et al., [dataset v1.1](https://doi.org/10.57745/FCV2R0), Etalab Open Licence 2.0; source updated 2026-08-25T11:13:19Z. Rows preserve adsorption/desorption direction and missing cells. Curves from one file keep the same group; no independent-trial count is inferred.

At 20 K the pressure normalizer and STP gas state remain unresolved. At 77/87 K the headers call the bar-valued coordinate relative pressure, so it is retained as reported_pressure in Pa with unresolved semantics. Its conversion is only a unit scaling, not a declaration of absolute pressure. Uptake is kept in its source-defined basis; excess/absolute and mass-basis details need confirmation.

| File / branch | Rows | Complete pairs | Missing cells | Pressure quantity | Uptake quantity |
|---|---:|---:|---:|---|---|
| H2.20K--MIL-100(Fe)+0.5%QDOTS.csv / adsorption | 24 | 24 | 0 | normalized_pressure | reference_specific_volume |
| H2.20K--MIL-100(Fe)+0.5%QDOTS.csv / desorption | 24 | 21 | 6 | normalized_pressure | reference_specific_volume |
| H2.20K--MIL-100(Fe).csv / adsorption | 24 | 24 | 0 | normalized_pressure | reference_specific_volume |
| H2.20K--MIL-100(Fe).csv / desorption | 24 | 20 | 8 | normalized_pressure | reference_specific_volume |
| H2.20K--MIL-101(Cr)+1%GO.csv / adsorption | 23 | 23 | 0 | normalized_pressure | reference_specific_volume |
| H2.20K--MIL-101(Cr)+1%GO.csv / desorption | 23 | 21 | 4 | normalized_pressure | reference_specific_volume |
| H2.20K--MIL-101(Cr).csv / adsorption | 23 | 23 | 0 | normalized_pressure | reference_specific_volume |
| H2.20K--MIL-101(Cr).csv / desorption | 23 | 20 | 6 | normalized_pressure | reference_specific_volume |
| H2.20K--MOF-5+1%EG.csv / adsorption | 24 | 24 | 0 | normalized_pressure | reference_specific_volume |
| H2.20K--MOF-5+1%EG.csv / desorption | 24 | 20 | 8 | normalized_pressure | reference_specific_volume |
| H2.20K--MOF-5.csv / adsorption | 24 | 24 | 0 | normalized_pressure | reference_specific_volume |
| H2.20K--MOF-5.csv / desorption | 24 | 20 | 8 | normalized_pressure | reference_specific_volume |
| H2.77K--MIL-100(Fe)+0.5%QDOTS.csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MIL-100(Fe)+0.5%QDOTS.csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MIL-100(Fe).csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MIL-100(Fe).csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MIL-101(Cr) +1% GO.csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MIL-101(Cr) +1% GO.csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MIL-101(Cr).csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MIL-101(Cr).csv / desorption | 24 | 23 | 2 | reported_pressure | specific_amount |
| H2.77K--MOF-5+1%EG.csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MOF-5+1%EG.csv / desorption | 24 | 20 | 8 | reported_pressure | specific_amount |
| H2.77K--MOF-5.csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.77K--MOF-5.csv / desorption | 24 | 21 | 6 | reported_pressure | specific_amount |
| H2.87K--MIL-100(Fe)+0.5%QDOTS.csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MIL-100(Fe)+0.5%QDOTS.csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MIL-100(Fe).csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MIL-100(Fe).csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MIL-101(Cr)+1%GO.csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MIL-101(Cr)+1%GO.csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MIL-101(Cr).csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MIL-101(Cr).csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MOF-5+1%EG.csv / adsorption | 24 | 23 | 2 | reported_pressure | specific_amount |
| H2.87K--MOF-5+1%EG.csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MOF-5.csv / adsorption | 24 | 24 | 0 | reported_pressure | specific_amount |
| H2.87K--MOF-5.csv / desorption | 24 | 24 | 0 | reported_pressure | specific_amount |

## SOFC polarization grid

Source: [Mendeley collection v1](https://doi.org/10.17632/j8b9v4cb9d.1), CC BY 4.0. Explicit declarations are degrees Celsius, mA/cm² and V; header encodings/glyphs vary. Measurement versus model origin is unresolved, so voltage columns are marked unresolved. Temperature conditions are reconstructed from column headings. A successful load does not make these independent measured validation curves.

| Source file | Curves | Records | Missing cells |
|---|---:|---:|---:|
| Ui_30H2_10H2O_60N2.txt | 4 | 1664 | 0 |
| Ui_50H2_0H2O_50N2.txt | 4 | 2472 | 0 |
| Ui_50H2_10H2O_40N2.txt | 4 | 2472 | 0 |
| Ui_50H2_20H2O_30N2.txt | 4 | 2472 | 0 |

Totals: {'mof_curves': 36, 'mof_rows': 860, 'sofc_curves': 16, 'sofc_rows': 9080}.

No pressure/STP basis is inferred, no negative or super-unity ratio is clipped, and no row is assigned an artificial time coordinate. Native adsorption/thermal validation remains blocked by scientific input gaps rather than by the table API.
