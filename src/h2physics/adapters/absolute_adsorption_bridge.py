"""Exact-condition, provenance-preserving absolute-loading handoff to a vessel."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np


from ..adsorption import AdsorptionBasis, AdsorptionState
from ..core import immutable_array, _real_numeric_array, finite


class AbsoluteAdsorptionBridgeError(ValueError):
    """Raised when an adsorption state lacks a safe absolute-inventory basis."""


def _state_digest(state: AdsorptionState) -> str:
    digest = hashlib.sha256()
    digest.update(repr((state.basis, state.temperature_k, state.source_observations,
                       state.uncertainty_semantics, state.uncertainty_source_ids)).encode())
    for name in ("partial_pressures_pa", "site_loadings_mol_kg",
                 "site_pressure_derivatives_mol_kg_pa", "site_temperature_derivatives_mol_kg_k",
                 "propagated_standard_uncertainty_mol_kg"):
        array = getattr(state, name)
        digest.update(name.encode())
        if array is None:
            digest.update(b"none")
        else:
            digest.update(np.asarray(array, dtype="<f8").tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class AbsoluteAdsorptionVesselBridge:
    """A single-condition provider backed by one qualified absolute state.

    The bridge performs no fit, interpolation, EOS calculation, or excess-to-
    absolute correction. It can feed an exact matching equilibrium request to
    `FiniteAdsorptionVessel`; any other condition fails closed.
    """

    state: AdsorptionState
    qualification_evidence_id: str
    _pressure_anchor_pa: np.ndarray = field(init=False, repr=False, compare=False)
    _state_fingerprint: str = field(init=False, repr=False, compare=False)
    _identity_binding: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.state) is not AdsorptionState:
            raise TypeError("Bridge requires an original AdsorptionState")
        if not isinstance(self.qualification_evidence_id, str) or not self.qualification_evidence_id.strip():
            raise ValueError("An explicit absolute-loading qualification evidence ID is required")
        if self.state.basis.loading_definition != "absolute":
            raise AbsoluteAdsorptionBridgeError(
                "Finite vessel input requires absolute uptake; surface excess/source-defined loading "
                "needs an independently evidenced conversion or isotherm"
            )
        self.state.__post_init__()
        rows = tuple(item for site in self.state.source_observations for item in site)
        if len(self.state.source_observations) != self.state.site_loadings_mol_kg.shape[1]:
            raise AbsoluteAdsorptionBridgeError("Retain source-row provenance for every adsorbent site")
        if not rows:
            raise AbsoluteAdsorptionBridgeError("Retain source-row provenance for every vessel loading")
        missing = [item for item in rows
                   if not item.source_dataset_id or not item.source_sha256]
        if missing:
            raise AbsoluteAdsorptionBridgeError(
                "Every source observation needs a dataset identity and checksum"
            )
        for site_index, site in enumerate(self.state.source_observations):
            represented = {item.species for item in site}
            if represented != set(self.state.basis.species):
                raise AbsoluteAdsorptionBridgeError(
                    f"Source rows must cover every species at site {site_index}"
                )
        pressures = np.array(self.state.partial_pressures_pa, dtype=float, copy=True)
        if pressures.shape != (len(self.state.basis.species),):
            raise AbsoluteAdsorptionBridgeError("Anchor partial pressures do not match the species basis")
        pressures = immutable_array(pressures, name="pressures")
        object.__setattr__(self, "_pressure_anchor_pa", pressures)
        object.__setattr__(self, "_identity_binding", (id(self.state), self.qualification_evidence_id))
        object.__setattr__(self, "_state_fingerprint", self._current_fingerprint())

    def _current_fingerprint(self) -> str:
        payload = (id(self.state), self.qualification_evidence_id, _state_digest(self.state))
        return hashlib.sha256(repr(payload).encode()).hexdigest()

    @property
    def basis(self) -> AdsorptionBasis:
        return self.state.basis

    @property
    def source_dataset_checksums(self) -> tuple[tuple[str, str], ...]:
        self.require_current()
        pairs = {(row.source_dataset_id, row.source_sha256)
                 for site in self.state.source_observations for row in site}
        return tuple(sorted(pairs))

    @property
    def anchored_partial_pressures_pa(self) -> np.ndarray:
        values = np.array(self._pressure_anchor_pa, copy=True)
        values = immutable_array(values, name="values")
        return values

    @property
    def anchored_temperature_k(self) -> float:
        return self.state.temperature_k

    def require_current(self) -> AbsoluteAdsorptionVesselBridge:
        if self.state.basis.loading_definition != "absolute":
            raise AbsoluteAdsorptionBridgeError("Adsorption basis changed from absolute uptake")
        if ((id(self.state), self.qualification_evidence_id) != self._identity_binding
                or self._current_fingerprint() != self._state_fingerprint):
            raise AbsoluteAdsorptionBridgeError(
                "Source-backed state or qualification evidence changed after bridge creation"
            )
        return self

    def equilibrium(self, partial_pressures_pa, temperature_k: float) -> AdsorptionState:
        """Return the retained absolute state at its exact calibration conditions."""
        self.require_current()
        pressure = _real_numeric_array(partial_pressures_pa, "partial_pressures_pa")
        temperature = finite(temperature_k, "temperature_k", positive=True)
        if (pressure.shape != self._pressure_anchor_pa.shape
                or not np.all(np.isfinite(pressure)) or np.any(pressure < 0.)
                or not np.array_equal(pressure, self._pressure_anchor_pa)
                or temperature != self.state.temperature_k):
            raise AbsoluteAdsorptionBridgeError(
                "Single-point calibration bridge cannot interpolate or extrapolate conditions"
            )
        return self.state

    def local_loading_sensitivity(self) -> AbsoluteAdsorptionLoadingSensitivity:
        """Expose only the qualified state's local site-loading derivatives."""
        self.require_current()
        return AbsoluteAdsorptionLoadingSensitivity.from_bridge(self)


@dataclass(frozen=True, slots=True)
class AbsoluteAdsorptionLoadingSensitivity:
    """Site-resolved first-order loading tangent at one qualified state.

    Pressure derivatives are with respect to each species partial pressure;
    temperature derivatives are with respect to kelvin. No free-gas EOS response,
    equilibrium re-query, interpolation range or finite-condition prediction is
    supplied by this view.
    """

    bridge: AbsoluteAdsorptionVesselBridge = field(repr=False)
    site_pressure_derivatives_mol_kg_pa: np.ndarray
    site_temperature_derivatives_mol_kg_k: np.ndarray
    _state_fingerprint: str = field(init=False, repr=False, compare=False)

    @classmethod
    def from_bridge(cls, bridge):
        state = bridge.state
        pressure = state.site_pressure_derivatives_mol_kg_pa
        temperature = state.site_temperature_derivatives_mol_kg_k
        if pressure is None or temperature is None:
            raise AbsoluteAdsorptionBridgeError(
                "Local sensitivity requires both provider-supplied pressure and temperature derivatives"
            )
        return cls(bridge, pressure, temperature)

    def __post_init__(self):
        if type(self.bridge) is not AbsoluteAdsorptionVesselBridge:
            raise TypeError("Sensitivity view must retain an absolute-loading bridge")
        self.bridge.require_current()
        state = self.bridge.state
        pressure = np.array(self.site_pressure_derivatives_mol_kg_pa, dtype=float, copy=True)
        temperature = np.array(self.site_temperature_derivatives_mol_kg_k, dtype=float, copy=True)
        if (state.site_pressure_derivatives_mol_kg_pa is None
                or state.site_temperature_derivatives_mol_kg_k is None
                or not np.array_equal(pressure, state.site_pressure_derivatives_mol_kg_pa)
                or not np.array_equal(temperature, state.site_temperature_derivatives_mol_kg_k)):
            raise AbsoluteAdsorptionBridgeError(
                "Sensitivity arrays must be the original provider derivatives at the qualified state"
            )
        object.__setattr__(self, "site_pressure_derivatives_mol_kg_pa",
                           immutable_array(pressure, name="site_pressure_derivatives"))
        object.__setattr__(self, "site_temperature_derivatives_mol_kg_k",
                           immutable_array(temperature, name="site_temperature_derivatives"))
        object.__setattr__(self, "_state_fingerprint", self.bridge._state_fingerprint)

    def require_current(self):
        self.bridge.require_current()
        state = self.bridge.state
        if (self._state_fingerprint != self.bridge._state_fingerprint
                or not np.array_equal(self.site_pressure_derivatives_mol_kg_pa,
                                      state.site_pressure_derivatives_mol_kg_pa)
                or not np.array_equal(self.site_temperature_derivatives_mol_kg_k,
                                      state.site_temperature_derivatives_mol_kg_k)):
            raise AbsoluteAdsorptionBridgeError("Local sensitivity no longer matches its qualified source state")
        return self

    def directional_loading_delta(self, delta_partial_pressures_pa, delta_temperature_k=0.):
        """Return first-order per-species/per-site loading changes in mol/kg.

        Directions are caller-selected perturbations around the exact anchor. The
        result is a local tangent only and is not a new equilibrium AdsorptionState.
        """
        self.require_current()
        pressure_delta = _real_numeric_array(delta_partial_pressures_pa,
                                             "delta_partial_pressures_pa")
        species = len(self.bridge.state.basis.species)
        if pressure_delta.shape != (species,) or not np.all(np.isfinite(pressure_delta)):
            raise ValueError("Pressure direction must match the qualified species order")
        temperature_delta = finite(delta_temperature_k, "delta_temperature_k")
        pressure_part = np.einsum(
            "sij,j->is", self.site_pressure_derivatives_mol_kg_pa, pressure_delta)
        temperature_part = self.site_temperature_derivatives_mol_kg_k.T * temperature_delta
        result = pressure_part + temperature_part
        return immutable_array(result, name="directional_loading_delta_mol_kg")


def bind_absolute_adsorption_state(
    state: AdsorptionState, *, qualification_evidence_id: str,
) -> AbsoluteAdsorptionVesselBridge:
    """Bind one provenance-complete absolute state; reject signed excess data."""
    return AbsoluteAdsorptionVesselBridge(state, qualification_evidence_id)
