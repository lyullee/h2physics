# Real-gas linepack withdrawal into a fuel-cell feed

This connection reuses `RealGasLinepackState` with `CoolPropIsothermalEOS`
and the existing finite fuel-cell owner. Native CoolProp supplies hydrogen
pressure, density and caloric properties. No new EOS is fitted or implemented.

`advance_real_gas_linepack_to_source(initial, *, duration_s,
inlet_mass_flow_kg_s, outlet_mass_flow_kg_s, minimum_mass_kg, location,
gas_state, properties, origin, evidence_id, state_projection_evidence_id)`
returns `RealGasLinepackSourceHandoff`. Both providers must be matching direct
HEOS Hydrogen instances. The initial inventory advances through its existing
mass-port API; the accepted ledger, pressure endpoints, held temperature and
exact time bin are retained. The representative outlet must reproduce from
the supplied native property provider and fall within the endpoint pressures.

Pass the issued receipt into `bind_linepack_fuel_cell_feed`, together with
the target owner and step. The existing feed API accepts this real-gas receipt
as well as its explicit ideal-gas reference receipt. The representative source
state and the conditioned fuel-cell inlet state are separate arguments: the
inlet pressure must match the declared cell boundary within roundoff tolerance.
The receiving packet uses the exact declared boundary pressure after that check.

The caller supplies the integrated source enthalpy, its reference identity,
the receiver reference, a signed reference offset and conditioning energy.
The interface checks:

`source enthalpy + reference offset + conditioning = receiver feed enthalpy`.

It does not turn a representative outlet enthalpy into an interval integral.
An external process model or measurement must establish that integrated energy.
The receipt also preserves exact clocks, withdrawn hydrogen mass, molar basis,
source identity and original native objects. `require_current()` replays the
native property and mass/energy checks and rejects changed evidence or providers.

The executable contract is in
`validation/cases/real_gas_linepack_fuel_cell_feed.py`. Its interval energy and
withdrawal schedule are authored inputs. It exercises mass/energy accounting,
cell execution, invalid outlet states, mismatched clocks, cloned receipts and
native-provider mutation. Consult the current progress record for execution
status. This is a fixed-temperature lumped inventory connection; flow-rate
prediction, regulator dynamics, pipe momentum and thermal control require their
respective external models. It does not establish measured facility performance.

Primary implementation references:

- https://coolprop.org/coolprop/LowLevelAPI.html
- https://doi.org/10.1063/1.3160306



The final native real-gas case passed with eleven invalid-state, clock, energy,
clone and provider/callable/ledger/evidence mutation rejections. The existing
ideal-feed regression also passed after the common feed-pressure roundoff guard;
its energy residual is 0 J. Targeted Ruff and scoped diff checks passed.
The public API index is now 361 modules / 1804 definitions; Hangang metadata
contains exactly one new real-gas feed case and no missing profile definitions.

The direct 848062-byte delta was applied remotely and fully verified at
/scratch/CLUSTER_USER/h2physics-jobs/verified-coolprop-02574687, manifest
025746875ba33bf767d4eda2ba7e77da18e226d1cd6e3199d1aad85cb29fbc5e.
This is a source-integrity receipt, not job execution. The new real-gas API,
later coupling repairs and their documentation postdate that pin and require
the next delta. Local reconstruction of the exact 02574687 tree is running to
support that small follow-up delta and reproducible campaign generation.
Overall progress remains a rough 30–40%; implementation classes 56/82 remain
separate from independent measured-data validation.

Known source spin must equal the conditioned inlet spin; a dedicated spin
conversion model is required before supporting a different spin basis. Feed
origin must equal the issued source origin, so mapping cannot relabel synthetic
evidence as measured. The final local case passed fifteen negative paths plus
the actual fuel-cell run; the existing ideal reference regression also passed.
