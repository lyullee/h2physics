# Station explanation and observation contract alignment

Status: actionable application-boundary request.

Targets: hydrogen-station-sim, SAGA-PY and optional monitoring adapters.

## Required changes

- Align the station's optional HAZOP request with the current SAGA evaluation route and
  request/response types. The reviewed default `/api/digital-twin/hazop/direct` differs
  from the reviewed receiver `/api/digital-twin/hazop/evaluate`.
- Prefer an injectable native evaluation callable when both projects share a process;
  retain optional HTTP only for applications that require it.
- Export observations through explicit physical quantities, units, clock, validity,
  sensor location and component identity. A Pa-valued differential-pressure channel
  must not be consumed as absolute pressure.
- Preserve measured observations, model predictions and injected fault truth as separate
  sources. Virtual gas-detector proxies must retain their origin.
- Explanations consume supplied deterministic results and evidence; they do not calculate
  missing release openings, phase partitions or annual frequencies.

## Local types and acceptance

The local `TimeSeries` carries channel quantity as well as SI units, origin, validity,
source and clock. `channel_values(name, quantity=...)` rejects a semantic mismatch.
The local loader requires pressure basis and rejects undeclared standard-volume-to-mass
conversion. Reuse these meanings through a structural native adapter.

Validate the actual receiving schemas, a live/native exchange, invalid observations and
the absence of injected truth separately. Record the exact versions used by the caller
and receiver. An explanation test does not establish physical model accuracy.
