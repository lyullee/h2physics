# Parcel coding checkpoint

2026-10-28: implemented a bounded saturated-parcel first level using existing
CoolProp, fluids and SciPy dependencies. No new dependency installation, native
calculation, example execution or scientific test was performed. The explicit
heat callback is a scientific boundary, not a claim that atmospheric evaporation
has been solved. The rejected standalone cold-air condensation result remains
rejected and is not reused.

Two deferred cases compare constant heat against independent mass loss and a
zero-relative-drag incident plane crossing. They are pending, not passed. A
follow-up must add nonzero native drag, step refinement, closure rejection,
mass-floor trial failure retention, buoyancy/admissibility evidence and qualified
hydrogen observations before promoting this family. No impact family is counted
from the incident plane alone.

A separate static peer review found mutable-owner callback mixing and implicit
constant-pressure enthalpy accounting. The code now rejects owner configuration
changes during a run and records internal-energy storage plus explicit ambient
pressure work. This correction has not been executed. The deferred reference
checks now include pressure-work accounting.
