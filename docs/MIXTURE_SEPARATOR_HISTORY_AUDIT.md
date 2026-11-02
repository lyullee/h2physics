# Mixture separator accepted-history audit

## Purpose

`h2physics.adapters.mixture_separator_history` checks accepted, phase-resolved
mixture-vessel snapshots and cumulative balances supplied by an external native
integration owner. It is a post-run audit seam. It does not perform an evolving
composition flash, integrate a vessel, locate phase events, or substitute for the
native solver contract described in
[`requests/032_finite_mixture_separator.md`](../requests/032_finite_mixture_separator.md).

Each row carries a `MixtureInventoryStateAdmission`, whose equilibrium packet was
issued by a CoolProp mixture provider. A trajectory may use a new immutable provider
per composition snapshot, but species order, component molar masses, property basis,
and fixed vessel volume must remain identical. Each provider still owns one declared
overall composition; no fixed-composition provider is presented as a dynamic flash.

## Public Python contract

`MixtureSeparatorAcceptedPoint` binds one exact time to the native inventory
admission, cumulative inlet and outlet component mole vectors, and cumulative net
energy into the vessel. Vectors follow the packet's species order. The energy scalar
is expressed in J on the provider's retained energy reference and must account for
all admitted energy transfers, including stream enthalpy, heat and work when those
terms exist in the native run.

`audit_mixture_separator_history(...)` requires the exact-time zero-origin initial
row, strictly increasing subsequent times, fixed volume, compatible property basis,
finite pressure and temperature, explicit phase identity, and per-species cumulative
port integrals. It checks the identities

```text
n_i(t) - n_i(0) - N_in,i(t) + N_out,i(t) = 0
U(t) - U(0) - E_net,into(t) = 0
```

against caller-specified absolute tolerances at every supplied accepted point. The
result retains the exact accepted-point objects and their summaries. Each call to
`require_current()` rechecks the nested inventory admissions and recomputes row
residuals; editing an accepted point or its native phase packet invalidates the
audit. It does not independently verify that the named native run generated the
records; source owner identity, native accepted-step ownership, port integration,
and solver diagnostics must remain attached by the receiving native engine.

## Scope limits and evidence

The matching source contract is Request032. The host-side fixed-composition
CoolProp mixture provider supplies native equilibrium packets and phase properties;
the audit only consumes them. No multiphase inventory evolution, selective phase
withdrawal law, accepted integration step, phase appearance/disappearance event,
or native failure prefix is created here. A successful audit is a conservation
consistency check on supplied records, not validation against an experiment or
qualification for separator design.

The deferred case `mixture-separator-native-history-ledger` is registered in
`validation/cases/mixture_separator_history.py`. It has not been executed locally or
on a cluster. Its synthetic static packet checks API closure and negative admission
paths only; a native owner must provide independently issued changing-composition
trajectories to this audit. The companion [finite mixture interval runner](FINITE_MIXTURE_INVENTORY.md)
implements caller-supplied bounded two-phase intervals, but does not replace an
adaptive native trajectory or localize phase events. Independent
separator measurements before Request032 can be closed.

The phase packet contract follows the documented low-level CoolProp mixture state
API: [CoolProp mixture properties](https://coolprop.org/fluid_properties/Mixtures.html)
and [AbstractState API](https://coolprop.org/apidoc/CoolProp.AbstractState.html).
The conservation equations above are the model audit identities implemented here.
