# Rejected native air-condensation diagnostic boundary

This reproduces a source-owner correction request. It adds no accepted model family or production phase/ODH result. The separately installed MIT SLABx-LH2 0.2.0 diagnostic is unmodified. It is a constant-Cp standalone comparison with a fixed20.37K H2 inlet and a fixed dry-air composition; it is not the accepted steady dispersion execution. The finite oxygen-room and ordinary-air human thermal adapters do not call it.

The authored audit uses a1kg feed, dry293.15K air at101325Pa and explicit input mole fractions N2=.7808, O2=.2095, Ar=.0097. Original native molecular masses and returned condensate masses reconstruct the remaining gas inventory; no substitute thermodynamic solve or correction is applied. Positive O2 condensate requires its remaining-gas partial pressure to match the selected native saturation pressure under that diagnostic's own ideal-partial-pressure assumption.

At H2 feed mass fraction0.5 the actual native temperature is55.0627032932K, O2 condensate0.100471968218kg/kgfeed, remaining-gas O2 partial pressure189.918215304Pa and actual native O2 saturation182.053964105Pa. The relative excess is4.3197363%: this phase state is rejected.

Native y_h2=93.4927055182mol% matches the original total-feed gas-mole basis. The actual remaining-gas inventory gives97.5313438694mol%. Those are different bases; the original native result is retained, not overwritten. Native source uses a pre-condensation total-mole denominator in each saturation cap. Coupled remaining-gas normalization/complementarity and explicit returned gas/feed bases need a native-owner fix. Finite condensed-phase volume, solid/liquid calorimetry and a full cloud/room coupling are not independently qualified here.

At feed mass fraction0.005 no air condenses and feed/gas H2 fractions agree. Original endpoint errors atw=0/1 remain ValueErrors. Actual native function/argument/raw-result references and original exceptions are retained during replay. Exact scalar/input detail is emitted only under ignored artifacts.

| Negative-evidence verification gate | Pass |
|---|---|
| warm no-air-condensate feed and gas compositions agree | True |
| original cold native O2 condensate is positive | True |
| original cold native O2 saturation failure reproduced | True |
| native H2 output follows original feed rather than remaining gas | True |
| native endpoint failures are original ValueErrors | True |
| native diagnostic source unchanged | True |
| executed host source unchanged | True |

| Executed host source | SHA256 before/after |
|---|---|
| scripts/check_air_condensation_boundary.py | bab66d5a1af84ef67e576f3a994fceeb8362e717dc0e9f93ef4b0237d897733e |

Actual native air_condensation.py SHA256 before/after: `c883b28baa6f002ad660f09b565f6226f41110f9d847f35b40a1290b4a4c8ec7`.

Reproduce with `python scripts/check_air_condensation_boundary.py` using the reviewed separately installed target. Source provenance remains in [preferred_dispersion.md](preferred_dispersion.md). Request022 specifies the receiving fix; no receiving repository or native implementation was changed. This is an internal conservation/phase-consistency failure, not an experimental comparison or a replacement mixture EOS.
