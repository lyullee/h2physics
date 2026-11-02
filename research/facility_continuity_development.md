# Facility continuity development record

Date: 2026-10-28. Status: implemented_unverified.

The existing equipment adapters already emit `ConnectionTransfer` records with
node/port identity, signed mass rate, upstream/transmitted thermodynamic states
and heat/shaft power. This increment adds only a facility-level continuity audit
over those original records. It deliberately does not create another hydraulic,
thermodynamic or transient solver.

Design decisions:

- topology and property basis are admitted before a frame;
- material, heat, shaft work and storage derivatives stay distinct;
- port reuse, unknown nodes and mixed energy references fail explicitly;
- per-node and per-component residuals remain available when strict closure is
  disabled for diagnostic use;
- no missing boundary or storage term is inferred as zero except an explicitly
  absent node storage rate, which declares a steady node for that frame.

Seven deferred cases cover a closed two-node transfer, external feed/takeoff,
finite accumulation, heat/work, reverse flow, identity rejection and retained
nonclosure. They have not been imported, discovered or executed. AST and lint
review are static evidence only.
