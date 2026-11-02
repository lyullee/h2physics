# Spatial counterflow heat-exchanger development

## Scope

This increment adds a steady one-dimensional counterflow thermal model. It is separate
from the existing adapter that binds and audits two already-computed process transfers.
The new owner divides declared conductance over explicit cells and solves both stream
enthalpy balances together. It does not replace finite closed-inventory exchanger
dynamics.

## Contracts

- The hot coordinate runs from hot inlet to hot outlet. Cold material moves in the
  opposite direction, so the cold inlet is the final array face.
- The caller supplies absolute pressure at every cell face and a `state_ph` closure for
  each stream. This module does not infer friction, phase selection, mixtures, reference
  enthalpy or an EOS.
- Each cell applies its declared conductance to the mean face-temperature difference.
  Stream enthalpy equations and global energy closure are solved simultaneously.
- A result is rejected if equations do not converge, energy does not close, heat reverses,
  or the two spatial temperature fields cross.

## Deferred evidence

Four cluster cases cover energy closure, mesh refinement, the small-conductance limit and
pressure-profile rejection. They are authored numerical checks and remain unexecuted until
the next cluster campaign. Real UA distributions, pressure-loss data, two-phase behavior,
axial conduction, ambient loss, transient hold-up and equipment measurements remain open.

The first completed 2026-10-29 Nurion attempt rejected the mesh-refinement and
small-conductance cases. The residual norm had been scaled by total inlet enthalpy
flow, which made a micro-watt duty fall below the nonlinear solver's relative
termination threshold. The implementation now scales the coupled residuals by the
declared total conductance and inlet temperature span, bounded below by the declared
absolute energy tolerance. Post-solve rejection reports energy-closure, nonpositive
cell heat flow and temperature crossing separately. Rerun all four cases from a new
source pin; this adjustment has not yet been numerically executed.
