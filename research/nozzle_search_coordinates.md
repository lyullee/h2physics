# Nozzle local-coordinate numerical correction

The first open-data inventory comparison exposed a default pressure-convergence failure
in CoolProp 8.0.0 HEOS normal hydrogen. The synthetic inlet state is a binned reconstruction
from [Jordan, T. (2023), KIT dataset](https://doi.org/10.35097/1187), CC BY 4.0, using the
declared observation operator in `scripts/compare_discha_release.py`. It is not an
independent nozzle-pressure measurement.

At upstream P = 5957812.127680701 Pa and T = 238.31506629999998 K, back pressure 101325 Pa,
the original log-pressure scalar minimization exhausted refinement. Its final relative
flux change was 4.967979679988721e-12, while relative pressure change was
2.759120783682445e-6, exceeding the unchanged 1e-6 pressure gate.

SciPy's bounded stopping rule includes a coordinate-magnitude term. Optimizing log(P)
directly around 15–20 imposes a larger absolute coordinate floor than an equivalent local
coordinate centered on zero. The correction maps every pressure bracket to [-1, 1] before
calling the same optimizer. It preserves the EOS, objective, candidate endpoints, refinement
and both acceptance tolerances. No fallback result or tolerance relaxation is introduced.

Observed corrected results (unit nominal effective-area reference):

| Initial points | Flux kg/(m² s) | Selected P Pa | Refined relative P change |
|---:|---:|---:|---:|
| 17 | 4122.400455263040 | 3059216.9013674874 | 3.6123156658e-9 |
| 33 | 4122.400455263041 | 3059216.889854457 | 3.7633912766e-9 |
| 65 | 4122.400455263044 | 3059216.950802975 | 1.9922914464e-8 |

The local-coordinate change alone did not resolve every input: a second observed-operator
state at P = 4517335.000498776 Pa and T = 236.41622040000001 K still exhausted refinement
with relative flux change 7.01728466549426e-12 and pressure change 3.5327736750474167e-6.
This negative result was retained before introducing the final single-phase refinement.

For a consistent single-phase EOS, continuity and isentropic energy give
`dG/dP = v/a² - 1/v`; an interior maximum therefore has `v² = a²`. When the provider
supplies sound speed on a valid single-phase sign-changing bracket, the kernel now uses
SciPy brentq on this condition. Two-phase sound speed is not invented. Brackets without
the optional sound-speed property still use the bounded local-coordinate objective.
Candidate flux consistency and the original grid/pressure/flux gates are retained.

Final observed single-phase refinement:

| Upstream P Pa | Initial points | Selected P Pa | Flux kg/(m² s) | Refined relative P change |
|---:|---:|---:|---:|---:|
| 5957812.127680701 | 17 | 3059216.9377303766 | 4122.400455263035 | 6.5163602698e-13 |
| 5957812.127680701 | 33 | 3059216.9377303724 | 4122.400455263040 | 1.3699425935e-15 |
| 5957812.127680701 | 65 | 3059216.9377303766 | 4122.400455263035 | 1.3699425935e-15 |
| 4517335.000498776 | 17 | 2326713.2630701230 | 3143.507146119327 | 1.8012325164e-15 |
| 4517335.000498776 | 33 | 2326713.2630701186 | 3143.507146119328 | 1.8012325164e-15 |
| 4517335.000498776 | 65 | 2326713.2635368950 | 3143.507146755739 | 2.0061627421e-10 |

The more precise liquid-path search also exposed a CoolProp phase-boundary fraction
of -6.048903157289708e-10. Strict default property behavior rejects it. An explicitly
selected `quality_roundoff_tolerance=1e-8` permits only that bounded endpoint adjustment,
retains the raw value in the state and reports the maximum adjustment in nozzle diagnostics.
Enthalpy/density are not edited. Larger violations still fail; no policy is selected silently.

`tests/test_release.py` reproduces both flat-peak states and checks cross-grid pressure and
flux agreement. `test_core_thermo.py` checks strict and explicitly budgeted quality behavior.
This corrects numerical resolution; it does not extend the physical validity of homogeneous
equilibrium, validate an experimental flow coefficient or resolve pipe losses.
