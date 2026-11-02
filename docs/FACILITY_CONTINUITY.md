# Facility continuity audit

`FacilityContinuityAudit` connects original `ConnectionTransfer` results without
rerunning their native equipment models. It checks a fixed topology at one
explicit clock sample and exposes per-node mass and enthalpy-rate residuals.

Positive external rates enter a node. Positive storage rates increase its finite
inventory. A nonzero material boundary must retain its transported thermodynamic
state and property/reference basis. Heat and shaft work are separate nonmaterial
boundaries. Each `(node_id, port_id)` can be occupied once.

Internal equipment transfers use the upstream and transmitted states already
recorded by their producer. Their enthalpy difference is compared with the
original equipment heat/shaft power; no replacement pressure, flow, heat-transfer
or control law is introduced.

This level is a steady sampled audit. It does not interpolate clocks, infer a
storage derivative, localize events, solve a network, or qualify a facility.
Callers must calculate storage rates on the same clock and declare all external
material, heat and work boundaries. Mixed fluids or energy references are rejected.

The `facility-continuity` Nurion profile is required before this source-only API
can be called executed. Independent plant measurements and each equipment
provider's own validation remain separate requirements.
