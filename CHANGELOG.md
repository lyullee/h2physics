# Changelog

## 0.2.0.dev0 — model-level extensions (development)

- Add indoor HyRAM conditional peak/accumulation adapter and evidence-bound FA/DDT screening.
- Add CoolProp finite-stock mechanical expansion reference, explicit energy partition,
  conditional spherical weak-wave normalization and linear SDOF structural response.
- Add optional solved TESPy cycles and current ExerPy physical exergy analysis.
- Reuse native multiphase thermochemistry for solid redox equilibrium and finite reaction coupling.
- Add measured Tafel/iR/Faradaic-efficiency/active-site turnover analysis.
- Add coupled PAR draft, native gas thermochemistry, finite catalyst heat storage and entropy gate.
- Record focused verification, unchanged baseline failures and installed-artifact audits in
  [the continuation report](docs/ENHANCEMENTS_20261102.md). This development snapshot is distinct
  from the already published PyPI/Zenodo 0.1.0 release.

## 0.1.0 — initial public research release

Published on GitHub, PyPI and Zenodo on 2026-11-02. Version DOI: [10.5281/zenodo.23886390](https://doi.org/10.5281/zenodo.23886390). Registry and archive identities are recorded in [the publication receipt](docs/REGISTRY_ARCHIVE_RECEIPT_0_1_0.md).

- Original composable Python models and optional native adapters for hydrogen process, storage, release and safety research.
- CoolProp property ownership and explicit material, phase, caloric-reference, unit and clock contracts.
- Separate input, equation, extreme-value, connection, selected regression and representative-run evidence.
- Four conditional measured-data comparisons; no claim of full experimental qualification or facility certification.
- Detailed user/API documentation, development history, research continuation and receiving-engine requests.
- External raw observations, source reference documents, installed engines, credentials and local computation artifacts excluded.

Publication status and exact archive hashes are maintained separately in the release record.
