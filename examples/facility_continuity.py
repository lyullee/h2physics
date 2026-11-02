"""Unexecuted construction example for a facility continuity frame."""

from h2physics.core import PropertyBasis, ThermoState
from h2physics.equipment import BoundaryPower, ConnectionTransfer
from h2physics.facility_continuity import (
    FacilityContinuityAudit,
    FacilityContinuityFrame,
    FacilityNode,
    FacilityStorageRate,
)

basis = PropertyBasis("Hydrogen", "example-reference", "normal")
state = ThermoState(basis, 2.0e6, 300.0, 1.6, 4.0e6, 2.75e6, 5.0e4, "gas")
transfer = ConnectionTransfer(
    "valve-1", "source", "receiver", "source:out", "receiver:in",
    0.01, state, state, BoundaryPower(), 0.0, True,
)
frame = FacilityContinuityFrame(
    "example-clock", 1.0, (transfer,), (),
    (
        FacilityStorageRate("source", basis, -0.01, -40000.0),
        FacilityStorageRate("receiver", basis, 0.01, 40000.0),
    ),
)
audit = FacilityContinuityAudit((FacilityNode("source", basis), FacilityNode("receiver", basis)))

# Deferred to the Nurion validation campaign:
# result = audit.audit(frame)
