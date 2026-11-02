# Current checkpoint — measured comparisons executed, qualification limited

## Measured-data comparison checkpoint — 2026-11-02

Four selected own-model closures were compared with real experiments using separated calibration/evaluation data: effectivepermeance(64train/32heldout),normalizedhydridekinetics(100train/44heldoutcurves),PEMpolarizationlosses(46train/56heldoutcontexts),andfixed-coefficientgasnozzle(13train/22heldoutscanrows). Results are conditional measured comparisons, not formal qualification; qualifiedcount remains0. Permeance heldoutMARE2.15–4.06%; hydride mean-curveRMSE4.49/4.86percentagepoints; PEMRMSE23.102mV; nozzleMARE29.83%. Native engine internal physics and whole-facility physics were excluded. All365productPythonfiles match the prior basic checkpoint; no productionmodel/default changed. See [PHYSICAL_VALIDATION_CAMPAIGN.md](PHYSICAL_VALIDATION_CAMPAIGN.md), its source/identifiability limits and artifacts/physical-validation-20261102/summary.json. Raw datasets remain ignored; two original public source-metadata ledgers and four replay scripts were added. No further calculation is running.

---

Earlier checkpoints below are historical.

# Current checkpoint — basic regression and representative runs complete

## Basic regression / representative-run checkpoint — 2026-11-02

The explicitly requested basic stage finished:50/50 selected existing regression tests across12 original files, and6/6 representative input-to-output runs passed; zero failures/errors/skips in final runs. Three independent tasks were used. No product source changed, and all recorded pins still match current source. This is selected regression and six examples, not78/78 full end-to-end qualification. One pre-existing compartment arithmetic-guard warning remains recorded; finite outputs and basic checks pass without deeper work. The previous72normal/2rejection/2blocked/2terminal connection classification is unchanged. See [REGRESSION_REPRESENTATIVE_CAMPAIGN.md](REGRESSION_REPRESENTATIVE_CAMPAIGN.md) and artifacts/regression-e2e-20261102/summary.json. No further testing is running or automatically scheduled.

---

Earlier checkpoints below are historical.

# Current scope — basic connection checks only

## Basic connection checkpoint — 2026-11-02

The latest user instruction limits connection tests to basic input/output delivery, units, material identity and clock support. Additional deep checks and full-chain campaigns are stopped. No current worker remains active. Existing execution evidence is preserved: selected normal handoffs cover72/78 topic families;2 are rejection-only boundaries,2 blocked/unavailable external paths and2 terminal outputs without an existing consumer. The recorded57 passing cases include deeper checks executed before this scope reduction and must not be described as57 basic-only tests. No further calculation is planned in this stage. See [CONNECTION_CONTRACT_CAMPAIGN.md](CONNECTION_CONTRACT_CAMPAIGN.md).

---

Earlier checkpoints below are historical.

# Current checkpoint — extreme-value stage completed

Latest explicit campaign:108/108 extreme/boundary cases passed across66 selected host families;12 native cores excluded. Breakdown:29 model numerical,31 supporting numerical,1 calculated-domain rejection,1 endpoint field mapping and4 domain-edge-only families. Product stack/solubility finite-arithmetic guards were repaired;14 affected nominal regressions passed. Final parallel run preserved all368 pinned files. See EXTREME_CONTRACT_CAMPAIGN.md and artifacts/extreme-contracts-20261102/final-pin/run.json. Module-connection checks have not started. Earlier checkpoint text below is historical.

---

# Current checkpoint — nominal calculation checks completed

The user resumed on 2026-11-02. The pause below is historical. Selected host known-answer checks now pass: 67 cases across 66 families (30 model-equation, 35 supporting, one identity); 12 selected native cores are excluded. Input checks remain 78/78. No later extreme-value or module-connection campaign has started. Read FORMULA_CONTRACT_CAMPAIGN.md and artifacts/formula-contracts-20261102/executed-summary.json for current evidence. Two product seal defects were repaired; no broader engine physics qualification is claimed.

---

# Paused calculation-check campaign — restart checkpoint

User paused work to shut down and move the computer. Do not start or resume tests until the user requests resumption.

## Completed earlier stage

Input checks: 78/78 scoped families, 161 malformed-input cases + 1 manifest check; final combined 162 passed, no skips. See INPUT_CONTRACT_CAMPAIGN.md and artifacts/input-contracts-20261102/all-78.xml. That result is unaffected by the unfinished formula stage.

## Formula-check state at pause

- Scope: project-owned calculations against independent reference answers. Existing GitHub engines' internal physics is excluded. Extreme-value and module-connection campaigns have not been started.
- Equipment/storage: latest completed run has 22 passed and 1 failed in 11.52 s. Failure is an unfinished test fixture calling nonexistent CoolPropProperties.state_pq in _two_phase_shared_darcy, not an established product-formula failure. File tests/test_formula_contract_equipment_storage.py currently contains 23 cases. Its private per-family metadata still reflects an older 19-pass snapshot; reconcile before publishing any aggregate. Also review the new hydride-compressor accounting case's independence before counting it.
- Production/materials: last fully completed scoped run had 13 passed (9 model-equation + 4 supporting calculations). File now contains 17 cases, including four added cases for gasification/economics/PSA/biological. The latest run was interrupted by user request; stdout dots are NOT final pass evidence. PID 51704 was verified as the owned pytest process and terminated. Retained XML may be from an earlier run; verify timestamps and case identities before using it. Private metadata marks the four additions pending.
- Safety/facility: final completed scoped run has 20 passed in 7.73 s across 19 families (10 model-equation fields + 9 supporting geometry/accounting fields). Its metadata explicitly separates 10 native-owned fields and 4 pending host-formula fields. No claim of 33/33 core-equation coverage.
- No final combined formula run was performed; no final 78-family formula completion result exists.
- Product source was not changed during these equation checks. New formula test files and their logs are retained. Earlier fixture issues and dependency failures are preserved separately; none was converted into a fabricated pass.

## Runtime/process state

All three work lanes acknowledged STOP. Root process inspection found no remaining Python pytest process targeting test_formula_contract_*. Native/process calculations must remain stopped. No remote computation was submitted for this wave.

The Conda environment h2physics-py312 gained matplotlib 3.11.2 and dependencies to satisfy a genuine HyRAM import required by a host-fluence check. Use MPLBACKEND=Agg when resuming that test. No native plotting module was faked or monkey-patched.

## Files for resumption

- tests/test_formula_contract_equipment_storage.py
- tests/test_formula_contract_production_materials.py
- tests/test_formula_contract_safety_facility.py
- artifacts/formula-contracts-20261102/ (partial and completed logs/XML)
- ../analysis/private-scope/formula-equipment-storage.json
- ../analysis/private-scope/formula-production-materials.json
- ../analysis/private-scope/formula-safety-facility.json

On resumption, first inspect this checkpoint and current files. Correct the unfinished fixture, verify independent-oracle scope, then resume only the formula checks. Keep pending, native-owned, supporting-only and actual model-equation comparisons separate. Do not begin the later extreme-value or module-connection stages without the user's direction.

Recorded at 2026-11-02T17:34:18.455075+09:00
