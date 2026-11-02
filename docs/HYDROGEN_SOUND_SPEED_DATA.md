# Hydrogen speed-of-sound literature data

## Source and admitted bytes

The public source is the “Hydrogen Speed-of-Sound Literature Data Compilation,” Zenodo
record [10.5281/zenodo.21355851](https://doi.org/10.5281/zenodo.21355851), version 1.0.0,
by Riley Latcham, Luca Bernardini, Markus Richter and Martin Trusler, under CC BY 4.0.
The local reader accepts the publisher ZIP only at 45,826 bytes with
SHA-256 `38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553`; metadata JSON
is pinned at 6,458 bytes with SHA-256
`1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad`. See
`research/data/hydrogen-sound-speed.toml` for acquisition details. The reader parses the
30 numeric `.txt` measurement members using the project's schema-limited parser; it does
not execute the separately bundled `pif_reader.py`.

## Python interface

```python
from h2physics.data import load_hydrogen_acoustic_dataset
from h2physics.adapters import compare_acoustic_file_with_eos
from h2physics.thermo import CoolPropProperties

dataset = load_hydrogen_acoustic_dataset("H2_speedofsound_dataset.zip",
                                         "repository-metadata.json")
trace = compare_acoustic_file_with_eos(
    dataset,
    "H2_speedofsound_dataset/H2_speedofsound_Carey_1974_nH2.txt",
    CoolPropProperties("Hydrogen"),
)
trace.require_current()
```

The reader binds whole-archive and metadata hashes, exact member bytes, PIF tables, source
row identifiers, DOI, authors and license. The comparator requires an exact member and the
same normal/para spin basis reported by that file. It converts the declared pressure unit
MPa to Pa through `acoustic_columns`, then forwards each complete point directly to the
existing CoolProp `state_pt` API. Results retain source row IDs, observed and predicted
speed of sound, residuals, and explicit exclusions. There is no EOS reimplementation,
parameter fitting, interpolation, extrapolation, or missing-condition reconstruction.
`require_current()` checks the source receipts and reproduces the pointwise outputs from
the same provider owner.

## Limits and interpretation

The compilation combines literature measurements with different composition, phase and
experimental provenance. Unknown spin composition is not guessed; mismatched composition
and EOS basis is rejected. Missing or invalid measurements and unsupported EOS states are
retained as exclusions with row IDs. The repository's earlier acoustic report records 1027
parsed points and 761 HEOS comparisons; those historical aggregate results are not recomputed
by the deferred case.

The source compilation does not establish whether these literature data were independent
of EOS development. Therefore a pointwise replay is an implementation/data consistency
diagnostic, not independent validation or a universal CoolProp accuracy statement. No
uncertainty interpretation or source-specific experimental accuracy is inferred here.

## Deferred cluster case and staging

Hangang case `hydrogen-acoustic-source-to-coolprop-pointwise-diagnostic` is registered under
`source-data-ingestion`. It needs these source attachments staged at
`/scratch/CLUSTER_USER/h2physics-source-attachments/hydrogen-sound-speed/1.0.0/`:

| File | Bytes | SHA-256 |
|---|---:|---|
| `H2_speedofsound_dataset.zip` | 45,826 | `38a5c10a9fb06c41a32f4fbba4ac0d1dabb3b38a7e80490ebc587a2e6dcfd553` |
| `repository-metadata.json` | 6,458 | `1d83651ff168e7eae59c3688e25957392169034ebbdbd05c2cefe3c8b75ee3ad` |

It selects only `H2_speedofsound_dataset/H2_speedofsound_Carey_1974_nH2.txt`. The returned
case metrics report row counts and source identity; they do not claim accuracy, fitting,
or model qualification. No local tests or calculations were run while implementing this
bridge; execution is deferred to Hangang.

## Executed local replay — 2026-11-01

The newer user instruction permits local verification when Hangang is busy.
The complete replay compared 761 rows and retained 266 exclusions across the
1027 source rows. See [quantitative report](HYDROGEN_ACOUSTIC_REPLAY.md).
Historical EOS-data overlap still prevents an independent validation claim.
The deferred single-member case now also reports quantitative residuals,
state ranges and a zero-comparison failure gate.


## 2026-11-01 acoustic phase lineage

`AcousticEOSPoint` now retains the source-declared phase and actual CoolProp
PT phase. Its `phase_matches` classifies liquid and gas families, including
CoolProp's subcritical-temperature/high-pressure `supercritical_liquid` and
supercritical-temperature/low-pressure `supercritical_gas` labels; unsupported
source states and fully supercritical states remain unclassified. The report
retains all 761 comparisons and flags phase conflicts without modifying rows.
The full replay was executed again after the phase fields were introduced.

The pinned VanDael liquid row loop-1:row-28 has source pressure 0.411535% below
normal-H2 saturation pressure at its stated temperature, and the native PT
flash selects gas. A separate registered diagnostic checks that the liquid
source label, gas EOS label and 65.6881% residual are all preserved together.
No pressure correction or forced metastable liquid calculation is applied.
This isolates a phase-selection conflict but does not establish whether source
rounding, transcription, experimental state or EOS saturation accuracy caused it.
The API guide, source guide and aggregate replay retain this open scientific issue.


## 2026-11-01 primary acoustic table and uncertainty audit

The independently accessible CC BY 4.0 Nguyen-2024 manuscript was acquired to
the ignored raw cache (2379686 bytes; SHA-256
718f08874e2881beeebd5d5067b8a847a131ed2bd4082ffa7a7dc6fb049bef90).
Table 4 headings, units and two-column layout were visually inspected. The new
source audit script verifies that all 57 compiled T/p/w triplets exactly match
the primary table and attaches its reported expanded sound-speed uncertainties
(k=2) for diagnostics. No manuscript, raw table or copied source text is included
in the public tree. The aggregate report is NGUYEN_ACOUSTIC_SOURCE_AUDIT.md.

Only 19/57 native CoolProp residuals fall within the experimental expanded
uncertainty; the largest |residual|/U(w) is 9.78707615045. Thus table integrity
passed, but matching measurement-uncertainty accuracy is not established.
Correlated experimental errors, EOS model uncertainty and coefficient revision
history remain unresolved. No universal accuracy threshold or fit is inferred.
The research record now closes the primary-table and coverage-factor checks;
validation_qualified remains false. Reproduce the audit with the thermo/data
runtime and pdfplumber, passing the ignored document path and public report path.

The latest real-gas delta transfer terminated with wrapper exit 255 before a
verified destination receipt. A separate required-wrapper hostname/whoami check
returned 'No usable cpu shared connection'; no new connection or authentication
was attempted. Manual user reconnection was requested. Remote work is stopped
until the user restores READY cpu; partial incoming chunks are preserved for
hash-checked resume. Local source analysis continues. Transfer error reporting
now omits full base64 command payloads and keeps a bounded wrapper error message.


## Primary acoustic-source audit environment

`research_pdf` is an opt-in research extraction extra, pinned to the executed
pdfplumber 0.11.10 version. Its installed license file and upstream license
were checked as MIT (https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt).
No third-party extraction code or source documents are vendored. The raw
primary manuscript has a separately recorded CC BY 4.0 grant and checksum;
its bytes and extracted numeric rows stay in the ignored data cache.

Reproduce the primary-table comparison from the repository root:

```powershell
python -m pip install -e ".[thermo,data,research_pdf]"
python scripts/audit_nguyen_acoustic_source.py --pdf data/raw/hydrogen-acoustic-primary/2024/nguyen-2024.pdf --output docs/NGUYEN_ACOUSTIC_SOURCE_AUDIT.md
```

The document download URL and required checksum are in
`research/hydrogen_acoustic_independence.toml`. The script rejects changed
source bytes, unexpected row counts and any mismatched compiled observation.
Its report contains aggregate residual/uncertainty diagnostics and source/EOS
fingerprints, not the source table. The experiment provides no model-error
budget or independent-error assumption for a statistical coverage claim.
