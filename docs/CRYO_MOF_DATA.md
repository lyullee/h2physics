# Cryogenic MOF adsorption observations

The reader binds one H₂ isotherm CSV from the version 1.1 replication record
[10.57745/FCV2R0](https://doi.org/10.57745/FCV2R0). Repository metadata declares
the [Etalab Open Licence 2.0](https://spdx.org/licenses/etalab-2.0.html); the
source receipt and per-file rights review remain authoritative. Raw attachments
stay in ignored acquisition storage and are not included in Git or distributions.

`h2physics.data.load_cryo_mof_isotherm(path, dataset=..., expected_sha256=...)`
requires the exact repository dataset identity, a filename listed by that
metadata, the publisher attachment size/checksum, and the independent SHA-256
from the acquisition receipt. Its immutable result retains every source token,
row index, branch direction and attachment hash. `require_current()` rechecks
the source bytes and reconstructs the rows before the table is reused.

The table contains separate, source-ordered adsorption and desorption branches.
It is not a time series. Blank branch cells remain missing, and signed numeric
values are retained without clipping. The reader recognizes only the current
reviewed header layouts:

- At 20 K, `p/p` remains a dimensionless normalized-pressure observation. The
  uptake is represented as reference-specific volume (`m³/kg`) while its STP
  gas state remains unresolved.
- At 77 K and 87 K, the source labels a pressure ratio in bar. The reader only
  scales the reported number to Pa and marks its physical pressure basis
  unresolved; it does not reinterpret the coordinate as absolute pressure.
  `mmol/g` is expressed as `mol/kg` with numerical identity, while the uptake
  convention remains unresolved.

No temperature or pressure interpolation, isotherm fitting, excess-to-absolute
conversion, adsorbent-capacity estimate, dormancy simulation or vessel
validation is performed by this ingestion API. The next qualification work needs
an independently supported 20 K normalizer/STP state, pressure interpretation
for the 77/87 K coordinate, uptake convention and material-mass basis. Preserve
the original experimental groups and do not treat rows from a curve as
independent replicates.

The synthetic `cryo-mof-isotherm-source-bound-reader` contract checks parsing,
units, missing values, receipts and mutation rejection. It does not open the
acquired measurements and does not validate adsorption physics.

## Evidence-gated Langmuir forward diagnostic

`h2physics.adapters.compare_cryo_mof_with_langmuir(table, model, ...)` connects
complete rows from one 77 K or 87 K branch to the existing
`ExtendedLangmuirIsotherm`. Three independent evidence IDs are required: one
must support interpreting each parser-scaled pressure value directly as
absolute H2 pressure in Pa; another must support interpreting the reported
mol/kg number as absolute H2 loading on the model's exact material-mass basis;
the third must support the publisher material label as the model material
identity. The model must declare only H2 and absolute uptake, and its material
ID must exactly equal the source label. A source/model mismatch is rejected.

Every valid same-row input is evaluated at the file's exact temperature. Missing
branch rows are skipped, but negative uptake rows are rejected under the
explicit absolute-loading interpretation. The trace keeps source file/hash,
direction, row IDs, original source uptake, exact model owner and all three
interpretation evidence IDs. `require_current()` checks the source bytes and
re-evaluates all predictions. No fit, pressure/temperature interpolation,
extrapolation, excess-to-absolute conversion or automatic mass-basis choice is
made. The adapter is only a forward diagnostic under caller-authorized
interpretations; it does not establish physical validity of the Langmuir model,
the MOF material, or an adsorption bed. The 20 K branch is excluded because
normalized-pressure denominator state and reference-gas volume state are both
unresolved. Hangang case `cryo-mof-source-to-langmuir-diagnostic-bridge` uses a
synthetic file solely to check this API contract; it is not measurement replay.

`table.observation_table(direction)` projects one branch into the shared
`ObservationTable` fitting API. It retains source-row IDs, one file-level
experimental group, the exact unresolved variable bases, source hashes and
missing-value masks. The returned table is a detached observation snapshot;
call the source table's `require_current()` before creating a new projection.

```python
from pathlib import Path
import tomllib
from h2physics.data import DATASETS, resolve_dataset, load_cryo_mof_isotherm

# The metadata resolution uses the public repository; reuse a reviewed Dataset
# object when continuing an already pinned acquisition.
seed = next(item for item in DATASETS if item.key == "cryo-mof-dormancy")
dataset = resolve_dataset(seed)
receipt = tomllib.loads(Path("research/data/cryo-mof-dormancy.toml").read_text())
filename = "H2.77K--MIL-100(Fe).csv"
file_receipt = next(item for item in receipt["files"] if item["name"] == filename)
if dataset.metadata_sha256 != receipt["metadata_sha256"]:
    raise ValueError("Repository metadata changed; review and repin before reuse")
table = load_cryo_mof_isotherm(
    Path("data/raw/cryo-mof-dormancy/1.1") / filename,
    dataset=dataset,
    expected_sha256=file_receipt["sha256"],
)
observations = table.observation_table("adsorption")
usable = observations.complete_rows("pressure_coordinate", "uptake")
```

`usable` is a selection mask only. Review the retained variable bases before
choosing a model observation operator or assigning calibration/holdout groups.
The source table checks attachment size before every bounded currentness read,
so a replaced oversized file is rejected before loading it into memory.
