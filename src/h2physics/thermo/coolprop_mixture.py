"""Fixed-composition HEOS mixture states through CoolProp's low-level API.

CoolProp's native mixture flashes are limited to PT and saturation input pairs.
This adapter can optionally obtain PH/PS/P-density states through bounded scalar
inversions over PT flashes, but does not emulate density-energy inversions or a
transport mixing rule.
References: https://coolprop.org/fluid_properties/Mixtures.html and
https://coolprop.org/coolprop/LowLevelAPI.html
"""

import hashlib
import json
import math
import threading
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import numpy as np
from scipy.optimize import brentq

from ..core import PropertyBasis, ThermoState, finite, immutable_array
from ..mixtures import GasComposition
from .coolprop import CoolPropProperties


@dataclass(frozen=True, slots=True)
class MixtureThermoState(ThermoState):
    """Mixture state with native molar quality distinct from mass quality."""

    vapor_mole_fraction: float | None = None

    def __post_init__(self):
        ThermoState.__post_init__(self)
        if self.vapor_mass_fraction is not None:
            raise ValueError("Mixture vapor mole fraction cannot be stored as mass quality")
        if self.vapor_mole_fraction is not None:
            quality = finite(self.vapor_mole_fraction, "vapor_mole_fraction")
            if not 0. <= quality <= 1.:
                raise ValueError("Mixture vapor mole fraction must lie in [0, 1]")


def _contains_grid_boolean(value):
    if isinstance(value, (bool, np.bool_)):
        return True
    if isinstance(value, np.ndarray):
        if value.dtype.kind == "b":
            return True
        return value.dtype.kind == "O" and any(_contains_grid_boolean(item) for item in value.flat)
    if isinstance(value, (list, tuple)):
        return any(_contains_grid_boolean(item) for item in value)
    return False


def _grid_numeric_array(value, name):
    if _contains_grid_boolean(value):
        raise ValueError(f"Inverse-grid {name} must contain real numeric values")
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise ValueError(f"Inverse-grid {name} must contain real numeric values")
    return np.array(raw, dtype=float, copy=True)


@dataclass(frozen=True, slots=True)
class MixtureInverseGrid:
    """Immutable, reusable PT samples that propose mixture inverse brackets.

    The grid carries its exact mixture/property basis and inverse temperature
    domain. It is a numerical hint rather than a property table: attached grids
    are only used after query-pressure endpoint flashes confirm a root bracket.
    """

    composition_sha256: str
    property_basis: PropertyBasis
    inverse_temperature_bounds_k: tuple[float, float]
    pressure_nodes_pa: np.ndarray
    temperature_nodes_k: np.ndarray
    property_values: Mapping[str, np.ndarray]

    def __post_init__(self):
        if (not isinstance(self.composition_sha256, str)
                or len(self.composition_sha256) != 64):
            raise ValueError("Inverse grid needs a SHA-256 composition identity")
        try:
            bytes.fromhex(self.composition_sha256)
        except ValueError as error:
            raise ValueError("Inverse grid composition identity must be hexadecimal SHA-256") from error
        if not isinstance(self.property_basis, PropertyBasis):
            raise TypeError("Inverse grid needs a PropertyBasis identity")
        bounds = tuple(finite(value, "inverse grid temperature bound", positive=True)
                       for value in self.inverse_temperature_bounds_k)
        if len(bounds) != 2 or bounds[0] >= bounds[1]:
            raise ValueError("Inverse grid temperature bounds must be an increasing pair")
        pressures = _grid_numeric_array(self.pressure_nodes_pa, "pressure nodes")
        temperatures = _grid_numeric_array(self.temperature_nodes_k, "temperature nodes")
        if (pressures.ndim != 1 or temperatures.ndim != 1
                or pressures.size < 2 or temperatures.size < 5
                or not np.all(np.isfinite(pressures)) or np.any(pressures <= 0.)
                or not np.all(np.diff(pressures) > 0.)
                or not np.all(np.isfinite(temperatures)) or np.any(temperatures <= 0.)
                or not np.all(np.diff(temperatures) > 0.)
                or temperatures[0] < bounds[0] or temperatures[-1] > bounds[1]):
            raise ValueError("Inverse-grid axes must be increasing, finite and inside the declared domain")
        required_fields = {"enthalpy_j_kg", "entropy_j_kg_k", "density_kg_m3"}
        if (not isinstance(self.property_values, Mapping)
                or set(self.property_values) != required_fields):
            raise ValueError("Inverse grid must contain enthalpy, entropy and density samples")
        values = {}
        for field, raw in self.property_values.items():
            array = _grid_numeric_array(raw, f"{field} samples")
            if array.shape != (pressures.size, temperatures.size) or not np.all(np.isfinite(array)):
                raise ValueError(f"Inverse-grid {field} samples have an invalid shape or nonfinite values")
            differences = np.diff(array, axis=1)
            decreasing = field == "density_kg_m3"
            if (np.any(differences >= 0.) if decreasing else np.any(differences <= 0.)):
                raise ValueError(f"Inverse-grid {field} samples are not strictly monotone by pressure row")
            if decreasing and np.any(array <= 0.):
                raise ValueError("Inverse-grid density values must be positive")
            values[field] = immutable_array(array, name=f"{field} samples")
        pressures = immutable_array(pressures, name="pressure nodes")
        temperatures = immutable_array(temperatures, name="temperature nodes")
        object.__setattr__(self, "inverse_temperature_bounds_k", bounds)
        object.__setattr__(self, "pressure_nodes_pa", pressures)
        object.__setattr__(self, "temperature_nodes_k", temperatures)
        object.__setattr__(self, "property_values", MappingProxyType(values))

    @property
    def shape(self):
        """Return the (pressure, temperature) sample count."""
        return (self.pressure_nodes_pa.size, self.temperature_nodes_k.size)

    @property
    def fingerprint(self):
        """Return a stable digest for this grid's identity and numeric samples."""
        digest = hashlib.sha256()
        digest.update(self.composition_sha256.encode("ascii"))
        digest.update(repr(self.property_basis).encode("utf-8"))
        digest.update(np.asarray(self.inverse_temperature_bounds_k, dtype="<f8").tobytes())
        digest.update(np.asarray(self.pressure_nodes_pa, dtype="<f8").tobytes())
        digest.update(np.asarray(self.temperature_nodes_k, dtype="<f8").tobytes())
        for field in ("enthalpy_j_kg", "entropy_j_kg_k", "density_kg_m3"):
            digest.update(field.encode("ascii"))
            digest.update(np.asarray(self.property_values[field], dtype="<f8").tobytes())
        return digest.hexdigest()

    def write_npz(self, path):
        """Write this bracket-hint grid as a pickle-free compressed NumPy archive.

        The archive contains numeric arrays and scalar Unicode metadata only. It
        does not make the samples a qualified property table or establish that
        another CoolProp release will produce equivalent states.
        """
        if not isinstance(path, (str, Path)):
            raise TypeError("Grid archive path must be a string or pathlib.Path")
        basis = self.property_basis
        with Path(path).open("wb") as stream:
            np.savez_compressed(
                stream,
                schema_version=np.asarray(1, dtype=np.int64),
                composition_sha256=np.asarray(self.composition_sha256),
                basis_fluid=np.asarray(basis.fluid),
                basis_reference_id=np.asarray(basis.reference_id),
                basis_spin_composition=np.asarray(basis.spin_composition),
                inverse_temperature_bounds_k=np.asarray(
                    self.inverse_temperature_bounds_k, dtype="<f8",
                ),
                pressure_nodes_pa=np.asarray(self.pressure_nodes_pa, dtype="<f8"),
                temperature_nodes_k=np.asarray(self.temperature_nodes_k, dtype="<f8"),
                enthalpy_j_kg=np.asarray(self.property_values["enthalpy_j_kg"], dtype="<f8"),
                entropy_j_kg_k=np.asarray(self.property_values["entropy_j_kg_k"], dtype="<f8"),
                density_kg_m3=np.asarray(self.property_values["density_kg_m3"], dtype="<f8"),
                fingerprint=np.asarray(self.fingerprint),
            )

    @classmethod
    def read_npz(cls, path):
        """Restore and revalidate a grid archive without enabling pickle loading."""
        if not isinstance(path, (str, Path)):
            raise TypeError("Grid archive path must be a string or pathlib.Path")
        required = {
            "schema_version", "composition_sha256", "basis_fluid",
            "basis_reference_id", "basis_spin_composition",
            "inverse_temperature_bounds_k", "pressure_nodes_pa",
            "temperature_nodes_k", "enthalpy_j_kg", "entropy_j_kg_k",
            "density_kg_m3", "fingerprint",
        }
        try:
            with np.load(Path(path), allow_pickle=False) as archive:
                if set(archive.files) != required:
                    raise ValueError("Inverse-grid archive has missing or unexpected entries")

                def scalar_text(name):
                    value = archive[name]
                    if value.shape != () or value.dtype.kind != "U":
                        raise ValueError(f"Inverse-grid archive field {name!r} must be scalar text")
                    return str(value.item())

                version = archive["schema_version"]
                if version.shape != () or version.dtype.kind not in "iu" or int(version) != 1:
                    raise ValueError("Unsupported inverse-grid archive schema version")
                bounds = archive["inverse_temperature_bounds_k"]
                if bounds.shape != (2,) or bounds.dtype.kind not in "iuf":
                    raise ValueError("Inverse-grid archive temperature bounds are malformed")
                grid = cls(
                    composition_sha256=scalar_text("composition_sha256"),
                    property_basis=PropertyBasis(
                        scalar_text("basis_fluid"),
                        scalar_text("basis_reference_id"),
                        scalar_text("basis_spin_composition"),
                    ),
                    inverse_temperature_bounds_k=tuple(bounds),
                    pressure_nodes_pa=archive["pressure_nodes_pa"],
                    temperature_nodes_k=archive["temperature_nodes_k"],
                    property_values={
                        "enthalpy_j_kg": archive["enthalpy_j_kg"],
                        "entropy_j_kg_k": archive["entropy_j_kg_k"],
                        "density_kg_m3": archive["density_kg_m3"],
                    },
                )
                saved_fingerprint = scalar_text("fingerprint")
        except (OSError, ValueError, KeyError, TypeError) as error:
            if isinstance(error, ValueError) and str(error).startswith(
                    ("Inverse-grid", "Unsupported inverse-grid")):
                raise
            raise ValueError(f"Could not read inverse-grid archive at {path!s}") from error
        if saved_fingerprint != grid.fingerprint:
            raise ValueError("Inverse-grid archive fingerprint does not match its contents")
        return grid


class CoolPropMixtureProperties(CoolPropProperties):
    """A frozen mole-basis gas mixture backed by CoolProp HEOS.

    ``composition.species`` are mapped to CoolProp fluid names through the
    optional ``fluid_names`` mapping. Molar masses are checked against each
    pure component before a mixture state is created. Binary interaction data
    remain owned by the installed CoolProp release; missing pairs fail closed.
    """

    _IDENTITY_FIELDS = frozenset({
        "composition_id", "species", "coolprop_fluids", "mole_fractions",
        "molar_masses_kg_mol", "coolprop_molar_masses_kg_mol",
        "molar_mass_relative_tolerance", "inverse_temperature_bounds_k",
        "composition_sha256", "fluid_names", "backend", "version",
        "internal_energy_policy", "quality_roundoff_tolerance", "_basis",
        "_state", "_cp", "_lock", "_mixture_cp", "_IDENTITY_FIELDS",
        "inverse_cache_size", "_inverse_cache", "_inverse_cache_lock", "_partition_token",
    })

    def __setattr__(self, name, value):
        if (getattr(self, "_composition_locked", False)
                and name in self._IDENTITY_FIELDS | {"_composition_locked"}):
            raise AttributeError(f"CoolProp mixture identity/configuration is immutable: {name}")
        object.__setattr__(self, name, value)

    def __init__(self, composition: GasComposition, *,
                 fluid_names: Mapping[str, str] | None = None,
                 molar_mass_relative_tolerance: float = 1e-4,
                 inverse_temperature_bounds_k: tuple[float, float] | None = None,
                 inverse_cache_size: int = 512):
        if type(composition) is not GasComposition:
            raise TypeError("Supply a GasComposition with declared component molar masses")
        names = tuple(composition.species)
        fractions = tuple(float(value) for value in composition.mole_fractions)
        masses = tuple(float(value) for value in composition.molar_masses_kg_mol)
        if (not fractions or any(not math.isfinite(value) or value < 0. for value in fractions)
                or not math.isclose(math.fsum(fractions), 1., rel_tol=0., abs_tol=1e-12)):
            raise ValueError("Captured composition mole fractions must be finite, nonnegative and normalized")
        if not masses or any(not math.isfinite(value) or value <= 0. for value in masses):
            raise ValueError("Captured component molar masses must be finite and positive")
        mass_tolerance = finite(molar_mass_relative_tolerance,
                                "molar_mass_relative_tolerance", positive=True)
        if mass_tolerance > 1e-3:
            raise ValueError("Molar-mass reconciliation tolerance cannot exceed 1e-3")
        if (isinstance(inverse_cache_size, bool) or not isinstance(inverse_cache_size, int)
                or inverse_cache_size < 0):
            raise ValueError("inverse_cache_size must be a nonnegative integer")
        if inverse_temperature_bounds_k is None:
            inverse_bounds = None
        else:
            if not isinstance(inverse_temperature_bounds_k, (tuple, list)) or len(inverse_temperature_bounds_k) != 2:
                raise ValueError("Inverse flashes require an explicit (minimum, maximum) temperature pair")
            inverse_bounds = tuple(finite(value, "inverse temperature bound", positive=True)
                                   for value in inverse_temperature_bounds_k)
            if inverse_bounds[0] >= inverse_bounds[1]:
                raise ValueError("Inverse temperature bounds must be increasing")
        composition_id = composition.composition_id
        if len(names) < 2:
            raise ValueError("Use CoolPropProperties for a pure fluid; this provider needs a mixture")
        mapping = dict(fluid_names or {})
        if set(mapping) - set(names):
            raise ValueError("CoolProp fluid-name mapping contains an undeclared composition species")
        resolved = tuple(mapping.get(name, name) for name in names)
        if any(not isinstance(name, str) or not name.strip() for name in resolved):
            raise ValueError("Every mixture component needs a nonblank CoolProp fluid name")
        if len(set(resolved)) != len(resolved):
            raise ValueError("Distinct composition species must map to distinct CoolProp fluids")

        try:
            import CoolProp
            import CoolProp.CoolProp as cp
        except ImportError as error:
            raise ImportError("Install h2physics[thermo] to use the CoolProp mixture provider") from error
        native_masses = []
        for fluid, declared_mass in zip(resolved, masses, strict=True):
            pure = CoolProp.AbstractState("HEOS", fluid)
            native_mass = float(pure.molar_mass())
            native_masses.append(native_mass)
            if not math.isclose(native_mass, declared_mass, rel_tol=mass_tolerance, abs_tol=1e-12):
                raise ValueError(f"Declared molar mass for {fluid!r} differs from CoolProp")

        fluid_specification = "&".join(resolved)
        super().__init__(fluid_specification, backend="HEOS")
        self._state.set_mole_fractions(list(fractions))
        composition_payload = {
            "composition_id": composition_id,
            "species": list(names),
            "coolprop_fluids": list(resolved),
            "mole_fractions": [value.hex() for value in fractions],
            "molar_masses_kg_mol": [value.hex() for value in masses],
            "coolprop_molar_masses_kg_mol": [value.hex() for value in native_masses],
        }
        fingerprint = hashlib.sha256(json.dumps(
            composition_payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        self.composition_id = composition_id
        self.species = names
        self.coolprop_fluids = resolved
        self.mole_fractions = fractions
        self.molar_masses_kg_mol = masses
        self.coolprop_molar_masses_kg_mol = tuple(native_masses)
        self.molar_mass_relative_tolerance = mass_tolerance
        self.inverse_temperature_bounds_k = inverse_bounds
        self.inverse_cache_size = inverse_cache_size
        self._inverse_cache = OrderedDict()
        self._inverse_cache_lock = threading.RLock()
        # Derived acceleration data are optional and populated only when a
        # caller explicitly prepares a domain on its execution host.
        self._inverse_grid = None
        self._inverse_cache_hits = 0
        self._inverse_cache_misses = 0
        self.composition_sha256 = fingerprint
        self.fluid_names = MappingProxyType(dict(zip(names, resolved, strict=True)))
        has_hydrogen = any(name.lower() in {"h2", "hydrogen", "parahydrogen", "orthohydrogen"}
                           for name in resolved)
        self._basis = PropertyBasis(
            f"CoolProp HEOS fixed mixture {composition_id} ({fingerprint})",
            f"CoolProp:{CoolProp.__version__}:HEOS:mixture-parameters-from-installed-release:{fingerprint}",
            "mixture-H2-spin-unresolved" if has_hydrogen else "no-molecular-H2",
        )
        self._mixture_cp = cp
        self._partition_token = object()
        self._composition_locked = True

    @property
    def molar_mass_kg_mol(self) -> float:
        """Read native molar mass on the captured composition, not last-used state."""
        with self._lock:
            self._state.set_mole_fractions(list(self.mole_fractions))
            return finite(self._state.molar_mass(), "CoolProp mixture molar mass", positive=True)

    def _evaluate(self, pair, first, second) -> ThermoState:
        with self._lock:
            # Reapply the immutable construction snapshot before every flash.
            self._state.set_mole_fractions(list(self.mole_fractions))
            self._state.update(pair, first, second)
            return self._snapshot()

    def _snapshot(self) -> MixtureThermoState:
        """Keep CoolProp's mixture mole quality separate from mass quality."""
        state = super()._snapshot()
        quality = float(self._state.Q()) if state.phase == "two_phase" else None
        return MixtureThermoState(
            basis=state.basis,
            pressure_pa=state.pressure_pa,
            temperature_k=state.temperature_k,
            density_kg_m3=state.density_kg_m3,
            enthalpy_j_kg=state.enthalpy_j_kg,
            internal_energy_j_kg=state.internal_energy_j_kg,
            entropy_j_kg_k=state.entropy_j_kg_k,
            phase=state.phase,
            cp_j_kg_k=state.cp_j_kg_k,
            cv_j_kg_k=state.cv_j_kg_k,
            viscosity_pa_s=state.viscosity_pa_s,
            conductivity_w_m_k=state.conductivity_w_m_k,
            speed_of_sound_m_s=state.speed_of_sound_m_s,
            vapor_mass_fraction=None,
            raw_vapor_mass_fraction=None,
            vapor_mole_fraction=quality,
        )

    def state_pt(self, pressure_pa: float, temperature_k: float) -> ThermoState:
        """Evaluate a frozen-composition mixture at absolute pressure and temperature."""
        return self._evaluate(
            self._mixture_cp.PT_INPUTS,
            finite(pressure_pa, "pressure_pa", positive=True),
            finite(temperature_k, "temperature_k", positive=True),
        )

    def state_rho_t(self, density_kg_m3: float, temperature_k: float) -> ThermoState:
        """Evaluate a frozen-composition mixture at mass density and temperature."""
        return self._evaluate(
            self._mixture_cp.DmassT_INPUTS,
            finite(density_kg_m3, "density_kg_m3", positive=True),
            finite(temperature_k, "temperature_k", positive=True),
        )

    def isothermal_sound_speed_rho_t(self, density_kg_m3: float,
                                     temperature_k: float) -> float:
        """Return ``sqrt((∂p/∂ρ)_T)`` for the admitted single-phase mixture."""
        with self._lock:
            state = self.state_rho_t(density_kg_m3, temperature_k)
            if state.phase not in {"gas", "supercritical", "supercritical_gas"}:
                raise ValueError("Isothermal mixture derivative requires a homogeneous gas phase")
            density = finite(self._state.rhomass(), "EOS mixture mass density", positive=True)
            compressibility = finite(
                self._state.isothermal_compressibility(),
                "isothermal mixture compressibility Pa^-1", positive=True,
            )
            if not math.isclose(density, state.density_kg_m3, rel_tol=1e-12, abs_tol=1e-14):
                raise ValueError("CoolProp mixture density changed during derivative evaluation")
            return finite(math.sqrt(1.0/(density*compressibility)),
                          "isothermal mixture characteristic speed m/s", positive=True)

    def state_pq(self, pressure_pa: float, vapor_mole_fraction: float) -> ThermoState:
        """Evaluate a saturation endpoint by pressure and native mole quality.

        Mixture quality is not silently relabelled as mass quality. It is retained
        as ``MixtureThermoState.vapor_mole_fraction`` for compatible consumers.
        """
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        quality = finite(vapor_mole_fraction, "vapor_mole_fraction")
        if not 0. <= quality <= 1.:
            raise ValueError("Vapor mole fraction must lie in [0, 1]")
        return self._evaluate(self._mixture_cp.PQ_INPUTS, pressure, quality)

    def phase_partition_pq(self, pressure_pa, vapor_mole_fraction, *, component_mole_balance_tolerance):
        """Retain native phase compositions and derive the actual mass quality.

        Read all phase information under this provider's existing native lock.
        Component masses are the installed CoolProp values captured at creation.
        """
        with self._lock:
            state = self.state_pq(pressure_pa, vapor_mole_fraction)
            return self._partition_current_state(state, component_mole_balance_tolerance)

    def phase_partition_tq(self, temperature_k, vapor_mole_fraction, *,
                           component_mole_balance_tolerance):
        """Retain native phase compositions and derive mass quality for a TQ flash."""
        with self._lock:
            state = self.state_tq(temperature_k, vapor_mole_fraction)
            return self._partition_current_state(state, component_mole_balance_tolerance)

    def _partition_current_state(self, state, component_mole_balance_tolerance):
        from .mixture_phase_partition import _issue_native_partition

        if state.phase != "two_phase":
            raise ValueError("Native phase partition requires a resolved two-phase state")
        return _issue_native_partition(
            state=state, composition_sha256=self.composition_sha256,
            species=self.species, overall_mole_fractions=self.mole_fractions,
            liquid_mole_fractions=tuple(self._state.mole_fractions_liquid()),
            vapor_mole_fractions=tuple(self._state.mole_fractions_vapor()),
            component_molar_masses_kg_mol=self.coolprop_molar_masses_kg_mol,
            vapor_mole_fraction=state.vapor_mole_fraction,
            component_mole_balance_tolerance=component_mole_balance_tolerance,
            liquid_enthalpy_j_kg=self._state.saturated_liquid_keyed_output(self._mixture_cp.iHmass),
            vapor_enthalpy_j_kg=self._state.saturated_vapor_keyed_output(self._mixture_cp.iHmass),
            liquid_density_kg_m3=self._state.saturated_liquid_keyed_output(self._mixture_cp.iDmass),
            vapor_density_kg_m3=self._state.saturated_vapor_keyed_output(self._mixture_cp.iDmass),
            provider=self, _provider_token=self._partition_token)

    def phase_partition_ph(self, pressure_pa, enthalpy_j_kg, *, quality_bounds,
                           component_mole_balance_tolerance, enthalpy_absolute_tolerance_j_kg,
                           quality_absolute_tolerance, branch_evidence_id, branch_samples=9,
                           maximum_iterations=100):
        """Explicitly invert one caller-admitted two-phase PQ branch.

        Sampled strict monotonicity is an admission diagnostic, not a proof of
        global uniqueness. Gas-only ``state_ph`` retains its existing semantics.
        """
        from .mixture_phase_partition import (
            MixturePartitionInverseError,
            _issue_native_inverse,
        )

        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        target = finite(enthalpy_j_kg, "enthalpy_j_kg")
        budget = finite(enthalpy_absolute_tolerance_j_kg, "enthalpy absolute tolerance", positive=True)
        xtol = finite(quality_absolute_tolerance, "quality absolute tolerance", positive=True)
        bounds = tuple(finite(q, "quality bound") for q in quality_bounds)
        if len(bounds) != 2 or not 0. <= bounds[0] < bounds[1] <= 1.:
            raise ValueError("Declare increasing native mole-quality bounds within [0, 1]")
        if type(branch_samples) is not int or branch_samples < 3:
            raise ValueError("Use at least three explicit branch samples")
        if type(maximum_iterations) is not int or maximum_iterations <= 0:
            raise ValueError("Declare a positive inverse iteration limit")
        if not isinstance(branch_evidence_id, str) or not branch_evidence_id.strip():
            raise ValueError("Declare evidence supporting this selected equilibrium branch")
        evaluations, root = [], None
        queried_qualities = []

        def evaluate(quality):
            partition = self.phase_partition_pq(pressure, quality,
                component_mole_balance_tolerance=component_mole_balance_tolerance)
            evaluations.append(partition)
            queried_qualities.append(float(quality))
            return partition.state.enthalpy_j_kg-target

        try:
            residuals = [evaluate(float(q)) for q in np.linspace(*bounds, branch_samples)]
            differences = np.diff(residuals)
            increasing = bool(np.all(differences > 0.))
            if not increasing and not np.all(differences < 0.):
                raise ValueError("Selected PQ branch is not strictly monotone at declared samples")
            if residuals[0]*residuals[-1] > 0.:
                raise ValueError("Target enthalpy lies outside the selected PQ bracket")

            def guarded(quality):
                residual = evaluate(quality)
                ordered = sorted((q, part.state.enthalpy_j_kg)
                                 for q, part in zip(queried_qualities, evaluations, strict=True))
                for (q0, h0), (q1, h1) in zip(ordered, ordered[1:]):
                    if q1 > q0 and ((h1 <= h0) if increasing else (h1 >= h0)):
                        raise ValueError("PQ inverse evaluations contradicted sampled branch monotonicity")
                return residual

            quality, root = brentq(guarded, *bounds, xtol=xtol,
                maxiter=maximum_iterations, full_output=True, disp=False)
            final_residual = guarded(quality)
            if not root.converged or abs(final_residual) > budget:
                raise ValueError("PQ branch inverse failed its declared convergence/enthalpy budget")
            return _issue_native_inverse(
                partition=evaluations[-1], target_enthalpy_j_kg=target,
                quality_bounds=bounds, bracket_residuals_j_kg=(residuals[0], residuals[-1]),
                evaluations=tuple(evaluations), native_root=root,
                enthalpy_residual_j_kg=final_residual,
                branch_evidence_id=branch_evidence_id,
            )
        except Exception as cause:
            raise MixturePartitionInverseError(cause, evaluations, root) from cause

    def state_tq(self, temperature_k: float, vapor_mole_fraction: float) -> ThermoState:
        """Evaluate a saturation endpoint by temperature and native mole quality."""
        temperature = finite(temperature_k, "temperature_k", positive=True)
        quality = finite(vapor_mole_fraction, "vapor_mole_fraction")
        if not 0. <= quality <= 1.:
            raise ValueError("Vapor mole fraction must lie in [0, 1]")
        return self._evaluate(self._mixture_cp.QT_INPUTS, quality, temperature)

    def saturated(self, pressure_pa: float, vapor_mass_fraction: float, *,
                  mass_quality_options: Mapping | None = None) -> ThermoState:
        """Evaluate mass-quality saturation on an explicitly selected PQ branch.

        Endpoint calls need no inverse configuration. Interior queries require
        ``mass_quality_options`` for ``phase_partition_pq_mass``. Native mole
        quality remains distinct in the returned ``MixtureThermoState``.
        """
        quality = finite(vapor_mass_fraction, "vapor_mass_fraction")
        if not 0. <= quality <= 1.:
            raise ValueError("Vapor mass fraction must lie in [0, 1]")
        if quality in (0., 1.) and mass_quality_options is None:
            return self.state_pq(pressure_pa, quality)
        if not isinstance(mass_quality_options, Mapping):
            raise ValueError("Interior mixture mass quality requires explicit mass_quality_options")
        return self.phase_partition_pq_mass(
            pressure_pa, quality, **dict(mass_quality_options)).state

    def saturated_at_temperature(self, temperature_k: float, vapor_mass_fraction: float, *,
                                 mass_quality_options: Mapping | None = None) -> ThermoState:
        """Evaluate a caller-selected TQ branch at a target mass quality."""
        quality = finite(vapor_mass_fraction, "vapor_mass_fraction")
        if not 0. <= quality <= 1.:
            raise ValueError("Vapor mass fraction must lie in [0, 1]")
        if quality in (0., 1.) and mass_quality_options is None:
            return self.state_tq(temperature_k, quality)
        if not isinstance(mass_quality_options, Mapping):
            raise ValueError("Interior mixture mass quality requires explicit mass_quality_options")
        return self.phase_partition_tq_mass(
            temperature_k, quality, **dict(mass_quality_options)).state

    def phase_partition_pq_mass(self, pressure_pa, vapor_mass_fraction, *, quality_bounds,
                                component_mole_balance_tolerance,
                                mass_quality_absolute_tolerance, quality_absolute_tolerance,
                                branch_evidence_id, branch_samples=9, maximum_iterations=100):
        """Invert native PQ mole quality to a declared mass-quality target.

        Bounds select one native mole-quality branch. No global phase-envelope
        search or mixture EOS is introduced. All phase compositions are fresh
        native CoolProp partitions, including changes along the selected branch.
        """
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        return self._partition_mass_quality(
            "pressure_pa", pressure, vapor_mass_fraction,
            quality_bounds=quality_bounds,
            component_mole_balance_tolerance=component_mole_balance_tolerance,
            mass_quality_absolute_tolerance=mass_quality_absolute_tolerance,
            quality_absolute_tolerance=quality_absolute_tolerance,
            branch_evidence_id=branch_evidence_id, branch_samples=branch_samples,
            maximum_iterations=maximum_iterations)

    def phase_partition_tq_mass(self, temperature_k, vapor_mass_fraction, *, quality_bounds,
                                component_mole_balance_tolerance,
                                mass_quality_absolute_tolerance, quality_absolute_tolerance,
                                branch_evidence_id, branch_samples=9, maximum_iterations=100):
        """Invert native TQ mole quality to a declared mass-quality target."""
        temperature = finite(temperature_k, "temperature_k", positive=True)
        return self._partition_mass_quality(
            "temperature_k", temperature, vapor_mass_fraction,
            quality_bounds=quality_bounds,
            component_mole_balance_tolerance=component_mole_balance_tolerance,
            mass_quality_absolute_tolerance=mass_quality_absolute_tolerance,
            quality_absolute_tolerance=quality_absolute_tolerance,
            branch_evidence_id=branch_evidence_id, branch_samples=branch_samples,
            maximum_iterations=maximum_iterations)

    def _partition_mass_quality(self, coordinate, fixed_value, vapor_mass_fraction, *,
                               quality_bounds, component_mole_balance_tolerance,
                               mass_quality_absolute_tolerance, quality_absolute_tolerance,
                               branch_evidence_id, branch_samples, maximum_iterations):
        from .mixture_mass_quality import MixtureMassQualityInverse
        from .mixture_phase_partition import MixturePartitionInverseError

        target = finite(vapor_mass_fraction, "vapor_mass_fraction")
        bounds = tuple(finite(q, "native mole-quality bound") for q in quality_bounds)
        budget = finite(mass_quality_absolute_tolerance,
                        "mass-quality absolute tolerance", positive=True)
        xtol = finite(quality_absolute_tolerance, "mole-quality absolute tolerance", positive=True)
        balance_tolerance = finite(component_mole_balance_tolerance,
                                   "component mole-balance tolerance", positive=True)
        if (not 0. <= target <= 1. or len(bounds) != 2
                or not 0. <= bounds[0] < bounds[1] <= 1.
                or budget >= 1. or xtol >= bounds[1]-bounds[0]):
            raise ValueError("Declare mass quality in [0,1], increasing mole bounds and strict tolerances")
        if (not isinstance(branch_evidence_id, str) or not branch_evidence_id.strip()
                or type(branch_samples) is not int or branch_samples < 3
                or type(maximum_iterations) is not int or maximum_iterations <= 0):
            raise ValueError("Declare branch evidence, at least three samples and a positive iteration limit")
        partition_at = (self.phase_partition_pq if coordinate == "pressure_pa"
                        else self.phase_partition_tq)
        evaluations, by_quality, root = [], {}, None

        def evaluate(quality):
            quality = float(quality)
            if quality not in by_quality:
                by_quality[quality] = partition_at(
                    fixed_value, quality,
                    component_mole_balance_tolerance=balance_tolerance)
            partition = by_quality[quality]
            partition.require_current()
            evaluations.append(partition)
            return finite(partition.vapor_mass_fraction-target, "mass-quality residual")

        try:
            with self._lock:
                residuals = [evaluate(q) for q in np.linspace(*bounds, branch_samples)]
                differences = np.diff(residuals)
                increasing = bool(np.all(differences > 0.))
                if not increasing and not np.all(differences < 0.):
                    raise ValueError("Selected mass-quality branch is not strictly monotone at declared samples")
                if min(residuals[0], residuals[-1]) > 0. or max(residuals[0], residuals[-1]) < 0.:
                    raise ValueError("Mass-quality target lies outside the selected native mole-quality branch")

                def guarded(quality):
                    residual = evaluate(quality)
                    ordered = sorted((q, p.vapor_mass_fraction) for q, p in by_quality.items())
                    for (_, first), (_, second) in zip(ordered[:-1], ordered[1:], strict=True):
                        contradicted = second <= first if increasing else second >= first
                        if contradicted:
                            raise ValueError("Native root evaluations contradict sampled mass-quality monotonicity")
                    return residual

                quality, root = brentq(guarded, *bounds, xtol=xtol,
                    maxiter=maximum_iterations, full_output=True, disp=False)
                residual = guarded(quality)
                if not root.converged or abs(residual) > budget:
                    raise ValueError("Mass-quality inverse failed its explicit root/residual budget")
                return MixtureMassQualityInverse(
                    partition=evaluations[-1], target_vapor_mass_fraction=target,
                    native_mole_quality_bounds=bounds,
                    mass_quality_absolute_tolerance=budget,
                    branch_evidence_id=branch_evidence_id,
                    fixed_coordinate=coordinate, fixed_coordinate_value=fixed_value,
                    evaluations=tuple(evaluations), native_root=root,
                    mass_quality_residual=residual)
        except Exception as cause:
            raise MixturePartitionInverseError(cause, evaluations, root) from cause

    @property
    def critical_temperature_k(self):
        """Raise because a fixed-composition mixture can have multiple critical points.

        Consumers must select a phase-envelope method that defines which point
        they need. Returning a single arbitrary endpoint would mislabel states.
        """
        raise NotImplementedError(
            "Mixture critical points may be multiple; select an explicit phase method"
        )

    @property
    def critical_pressure_pa(self):
        """Raise because a fixed-composition mixture can have multiple critical points.

        Consumers must select a phase-envelope method that defines which point
        they need. Returning a single arbitrary endpoint would mislabel states.
        """
        raise NotImplementedError(
            "Mixture critical points may be multiple; select an explicit phase method"
        )

    def state_ph(self, pressure_pa: float, enthalpy_j_kg: float) -> ThermoState:
        return self._invert_isobaric(pressure_pa, enthalpy_j_kg, "enthalpy_j_kg")

    def state_ps(self, pressure_pa: float, entropy_j_kg_k: float) -> ThermoState:
        return self._invert_isobaric(pressure_pa, entropy_j_kg_k, "entropy_j_kg_k")

    def _invert_isobaric(self, pressure_pa: float, target: float, field: str,
                         *, decreasing: bool = False) -> ThermoState:
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        target = finite(target, field)
        if self.inverse_temperature_bounds_k is None:
            raise NotImplementedError(
                "Configure inverse_temperature_bounds_k before requesting mixture inverse states"
            )
        cache_key = (field, pressure.hex(), target.hex(), decreasing)
        if self.inverse_cache_size:
            with self._inverse_cache_lock:
                cached = self._inverse_cache.get(cache_key)
                if cached is not None:
                    self._inverse_cache.move_to_end(cache_key)
                    self._inverse_cache_hits += 1
                    return cached
                self._inverse_cache_misses += 1
        grid_state = self._inverse_grid_guess(pressure, target, field, decreasing)
        if grid_state is not None:
            return self._remember_inverse_result(cache_key, grid_state)
        lower, upper = self.inverse_temperature_bounds_k
        temperatures = np.linspace(lower, upper, 5)
        sampled = [self.state_pt(pressure, float(temperature)) for temperature in temperatures]
        gas_phases = {"gas", "supercritical", "supercritical_gas"}
        if any(state.phase not in gas_phases for state in sampled):
            raise ValueError("Mixture inverse bounds must remain within one gas/supercritical phase")
        if any(state.cp_j_kg_k is None or state.cp_j_kg_k <= 0. for state in sampled):
            raise ValueError("Mixture inverse requires positive finite cp throughout its sampled domain")
        values = np.asarray([getattr(state, field) for state in sampled], dtype=float)
        differences = np.diff(values)
        if (not np.all(np.isfinite(values))
                or (np.any(differences >= 0.) if decreasing else np.any(differences <= 0.))):
            direction = "decrease" if decreasing else "increase"
            raise ValueError(f"Mixture {field} must {direction} strictly across the sampled inverse domain")
        low_value, high_value = (values[-1], values[0]) if decreasing else (values[0], values[-1])
        if not low_value <= target <= high_value:
            raise ValueError(f"Requested {field} lies outside the declared inverse-temperature domain")
        for value, state in zip(values, sampled, strict=True):
            if target == value:
                return self._remember_inverse_result(cache_key, state)
        state_cache = {float(temperature): state
                       for temperature, state in zip(temperatures, sampled, strict=True)}

        def residual(trial_temperature):
            trial = float(trial_temperature)
            state = state_cache.get(trial)
            if state is None:
                state = self.state_pt(pressure, trial)
                state_cache[trial] = state
            self._require_inverse_state(state)
            return getattr(state, field) - target

        temperature = brentq(
            residual,
            lower, upper, xtol=1e-8, rtol=4 * np.finfo(float).eps, maxiter=100,
        )
        result = state_cache.get(float(temperature))
        if result is None:
            result = self.state_pt(pressure, temperature)
        return self._remember_inverse_result(cache_key, result)

    def prepare_inverse_grid(self, pressure_nodes_pa, temperature_nodes_k):
        """Prepare optional PT-sampled inverse brackets over a declared domain.

        This method performs CoolProp flashes. Call it on the intended compute
        host (for this project, through a deferred Nurion validation case),
        not during package import or provider construction. The grid is a
        bracket hint only: every selected bracket is checked against fresh PT
        flashes at the requested pressure before it is used.
        """
        pressures = _grid_numeric_array(pressure_nodes_pa, "pressure nodes")
        temperatures = _grid_numeric_array(temperature_nodes_k, "temperature nodes")
        if (pressures.ndim != 1 or temperatures.ndim != 1
                or pressures.size < 2 or temperatures.size < 5
                or not np.all(np.isfinite(pressures))
                or not np.all(np.isfinite(temperatures))
                or np.any(pressures <= 0.) or np.any(temperatures <= 0.)
                or np.any(np.diff(pressures) <= 0.)
                or np.any(np.diff(temperatures) <= 0.)):
            raise ValueError("Inverse grid requires increasing positive pressure and temperature nodes")
        if self.inverse_temperature_bounds_k is None:
            raise ValueError("Configure inverse_temperature_bounds_k before preparing an inverse grid")
        if (temperatures[0] < self.inverse_temperature_bounds_k[0]
                or temperatures[-1] > self.inverse_temperature_bounds_k[1]):
            raise ValueError("Inverse-grid temperatures must lie inside the declared inverse domain")
        gas_phases = {"gas", "supercritical", "supercritical_gas"}
        fields = ("enthalpy_j_kg", "entropy_j_kg_k", "density_kg_m3")
        values_by_field = {field: np.empty((pressures.size, temperatures.size), dtype=float)
                           for field in fields}
        for row, pressure in enumerate(pressures):
            states = [self.state_pt(float(pressure), float(temperature))
                      for temperature in temperatures]
            if any(state.phase not in gas_phases for state in states):
                raise ValueError("Inverse grid crosses outside the single-gas/supercritical branch")
            for state in states:
                if state.cp_j_kg_k is None or state.cp_j_kg_k <= 0.:
                    raise ValueError("Inverse grid requires positive finite cp throughout its sampled domain")
            for field in fields:
                values_by_field[field][row] = [getattr(state, field) for state in states]
                differences = np.diff(values_by_field[field][row])
                decreasing = field == "density_kg_m3"
                if (not np.all(np.isfinite(values_by_field[field][row]))
                        or (np.any(differences >= 0.) if decreasing else np.any(differences <= 0.))):
                    raise ValueError(f"Mixture {field} is not strictly monotone over a sampled pressure row")
        grid = MixtureInverseGrid(
            self.composition_sha256, self.basis, self.inverse_temperature_bounds_k,
            pressures, temperatures, values_by_field,
        )
        with self._inverse_cache_lock:
            self._inverse_grid = grid
        return grid

    def use_inverse_grid(self, grid: MixtureInverseGrid):
        """Attach previously prepared immutable grid data to a compatible provider."""
        if not isinstance(grid, MixtureInverseGrid):
            raise TypeError("grid must be a MixtureInverseGrid")
        if (grid.composition_sha256 != self.composition_sha256
                or grid.property_basis != self.basis
                or grid.inverse_temperature_bounds_k != self.inverse_temperature_bounds_k):
            raise ValueError("Inverse grid composition, property basis or temperature domain differs")
        with self._inverse_cache_lock:
            self._inverse_grid = grid
        return grid

    def _inverse_grid_guess(self, pressure, target, field, decreasing):
        grid = self._inverse_grid
        if grid is None or field not in grid.property_values:
            return None
        pressures = grid.pressure_nodes_pa
        temperatures = grid.temperature_nodes_k
        if not pressures[0] <= pressure <= pressures[-1]:
            return None
        values = grid.property_values[field]
        log_pressure = math.log(pressure)
        log_nodes = np.log(pressures)
        increasing = not decreasing
        right = int(np.searchsorted(log_nodes, log_pressure, side="right"))
        left = max(0, min(right - 1, pressures.size - 2))
        fraction = (log_pressure - log_nodes[left]) / (log_nodes[left + 1] - log_nodes[left])
        profile = values[left] + fraction * (values[left + 1] - values[left])
        ordered_values = -profile if decreasing else profile
        ordered_target = -target if decreasing else target
        if ordered_target < ordered_values[0] or ordered_target > ordered_values[-1]:
            return None
        index = int(np.searchsorted(ordered_values, ordered_target, side="right"))
        index = max(1, min(index, temperatures.size - 1))
        property_low_index, property_high_index = index - 1, index

        def to_temperature_index(item):
            return temperatures.size - 1 - item if decreasing else item

        low_index = min(to_temperature_index(property_low_index),
                        to_temperature_index(property_high_index))
        high_index = max(to_temperature_index(property_low_index),
                         to_temperature_index(property_high_index))
        low_t, high_t = temperatures[low_index], temperatures[high_index]
        state_cache = {}

        def state_at(temperature):
            key = float(temperature)
            if key not in state_cache:
                state_cache[key] = self.state_pt(pressure, key)
            return state_cache[key]

        # Check the interpolated bracket at the actual pressure. Expand by one
        # grid cell at a time; return None to use the full declared interval.
        while True:
            low_state = state_at(low_t)
            high_state = state_at(high_t)
            self._require_inverse_state(low_state)
            self._require_inverse_state(high_state)
            low_residual = getattr(low_state, field) - target
            high_residual = getattr(high_state, field) - target
            if low_residual == 0.:
                return low_state
            if high_residual == 0.:
                return high_state
            if low_residual * high_residual < 0.:
                def residual(trial_temperature):
                    state = state_at(trial_temperature)
                    self._require_inverse_state(state)
                    return getattr(state, field) - target

                root = brentq(residual, float(low_t), float(high_t), xtol=1e-8,
                              rtol=4 * np.finfo(float).eps, maxiter=100)
                result = state_at(root)
                self._require_inverse_state(result)
                return result
            if low_index == 0 and high_index == temperatures.size - 1:
                return None
            if increasing == (low_residual < 0.):
                if high_index == temperatures.size - 1:
                    return None
                high_index += 1
                high_t = temperatures[high_index]
            else:
                if low_index == 0:
                    return None
                low_index -= 1
                low_t = temperatures[low_index]

    @staticmethod
    def _require_inverse_state(state):
        if state.phase not in {"gas", "supercritical", "supercritical_gas"}:
            raise ValueError("Mixture inverse flash crossed the declared single-gas/supercritical branch")
        if state.cp_j_kg_k is None or state.cp_j_kg_k <= 0.:
            raise ValueError("Mixture inverse flash encountered unavailable or nonpositive cp")

    def _remember_inverse_result(self, key, result):
        if not self.inverse_cache_size:
            return result
        with self._inverse_cache_lock:
            self._inverse_cache[key] = result
            self._inverse_cache.move_to_end(key)
            while len(self._inverse_cache) > self.inverse_cache_size:
                self._inverse_cache.popitem(last=False)
        return result

    @property
    def inverse_cache_info(self):
        """Return exact-key inverse cache counters and current capacity."""
        with self._inverse_cache_lock:
            return MappingProxyType({
                "hits": self._inverse_cache_hits,
                "misses": self._inverse_cache_misses,
                "maxsize": self.inverse_cache_size,
                "currsize": len(self._inverse_cache),
            })

    def clear_inverse_cache(self):
        """Clear cached immutable PH/PS/P-density results and reset counters."""
        with self._inverse_cache_lock:
            self._inverse_cache.clear()
            self._inverse_cache_hits = 0
            self._inverse_cache_misses = 0

    def clear_inverse_grid(self):
        """Discard optional sampled inverse brackets without changing provider identity."""
        with self._inverse_cache_lock:
            self._inverse_grid = None

    def state_pu(self, pressure_pa: float, internal_energy_j_kg: float) -> ThermoState:
        """Invert pressure/internal energy only on the declared gas T branch.

        The configured temperature interval is sampled for strict monotonicity,
        checked for a single-gas/supercritical phase and bracketed by native PT
        calls. Without that interval the input pair remains unsupported. This
        is not a two-phase inventory flash and sampled monotonicity does not
        establish global uniqueness outside the selected interval.
        """
        return self._invert_isobaric(pressure_pa, internal_energy_j_kg,
                                     "internal_energy_j_kg")

    def state_rho_u(self, density_kg_m3: float, internal_energy_j_kg: float) -> ThermoState:
        """Refuse unsupported rho-U flashes; they require a phase-aware 2-D root.

        This implementation intentionally does not search for an arbitrary root
        or extrapolate beyond the installed CoolProp mixture phase envelope.
        """
        finite(density_kg_m3, "density_kg_m3", positive=True)
        finite(internal_energy_j_kg, "internal_energy_j_kg")
        raise NotImplementedError(
            "CoolProp mixture density-energy flashes are outside the documented input pairs"
        )

    def state_rho_u_bounded(self, density_kg_m3, internal_energy_j_kg, *, pressure_bounds_pa,
                            branch_evidence_id, density_absolute_tolerance_kg_m3,
                            internal_energy_absolute_tolerance_j_kg,
                            pressure_absolute_tolerance_pa, branch_samples=9,
                            maximum_iterations=100):
        """Explicit nested PT inverse on a caller-evidenced single-gas branch.

        Inner P-density inversions retain the existing temperature-domain gates.
        Sampled outer monotonicity is required but does not prove uniqueness.
        Default ``state_rho_u`` remains unsupported and never selects this path.
        """
        from .mixture_inventory_inverse import (
            MixtureInventoryInverseError,
            _issue_mixture_inventory_inverse,
        )

        density = finite(density_kg_m3, "density_kg_m3", positive=True)
        energy = finite(internal_energy_j_kg, "internal_energy_j_kg")
        bounds = tuple(finite(p, "pressure bound", positive=True) for p in pressure_bounds_pa)
        if len(bounds) != 2 or bounds[0] >= bounds[1]:
            raise ValueError("Declare increasing absolute-pressure bounds")
        rho_budget = finite(density_absolute_tolerance_kg_m3, "density absolute tolerance", positive=True)
        u_budget = finite(internal_energy_absolute_tolerance_j_kg, "internal energy absolute tolerance", positive=True)
        xtol = finite(pressure_absolute_tolerance_pa, "pressure absolute tolerance", positive=True)
        if not isinstance(branch_evidence_id, str) or not branch_evidence_id.strip():
            raise ValueError("Declare evidence for this fixed-density gas branch")
        if type(branch_samples) is not int or branch_samples < 3:
            raise ValueError("At least three explicit pressure branch samples are required")
        if type(maximum_iterations) is not int or maximum_iterations <= 0:
            raise ValueError("Declare a positive pressure root iteration limit")
        if self.inverse_temperature_bounds_k is None:
            raise ValueError("Bounded density-energy inversion requires explicit temperature bounds")
        evaluations, root = [], None
        queried_pressures = []

        def evaluate(pressure):
            state = self.state_prho(pressure, density)
            self._require_inverse_state(state)
            if state.cv_j_kg_k is None or state.cv_j_kg_k <= 0.:
                raise ValueError("Fixed-density inverse requires positive native cv")
            if abs(state.density_kg_m3-density) > rho_budget:
                raise ValueError("Inner pressure-density inverse exceeds its explicit residual budget")
            evaluations.append(state)
            queried_pressures.append(float(pressure))
            return state.internal_energy_j_kg-energy

        try:
            residuals = [evaluate(float(p)) for p in np.linspace(*bounds, branch_samples)]
            differences = np.diff(residuals)
            increasing = bool(np.all(differences > 0.))
            if not increasing and not np.all(differences < 0.):
                raise ValueError("Selected fixed-density branch is not strictly monotone at sampled pressures")
            if residuals[0]*residuals[-1] > 0.:
                raise ValueError("Target internal energy lies outside the selected pressure bracket")

            def guarded(pressure):
                residual = evaluate(pressure)
                ordered = sorted((p, s.internal_energy_j_kg)
                                 for p, s in zip(queried_pressures, evaluations, strict=True))
                for (p0, u0), (p1, u1) in zip(ordered, ordered[1:]):
                    if p1 > p0 and ((u1 <= u0) if increasing else (u1 >= u0)):
                        raise ValueError("Native root evaluations contradicted sampled energy branch monotonicity")
                return residual

            pressure, root = brentq(guarded, *bounds, xtol=xtol,
                maxiter=maximum_iterations, full_output=True, disp=False)
            residual = guarded(pressure)
            if not root.converged or abs(residual) > u_budget:
                raise ValueError("Bounded density-energy inverse exceeded its convergence/energy budget")
            state = evaluations[-1]
            return _issue_mixture_inventory_inverse(
                state=state, target_density_kg_m3=density,
                target_internal_energy_j_kg=energy, pressure_bounds_pa=bounds,
                bracket_energy_residuals_j_kg=(residuals[0], residuals[-1]),
                evaluations=tuple(evaluations), native_root=root,
                density_residual_kg_m3=state.density_kg_m3-density,
                internal_energy_residual_j_kg=residual,
                branch_evidence_id=branch_evidence_id,
            )
        except Exception as cause:
            raise MixtureInventoryInverseError(cause, evaluations, root) from cause

    def state_prho(self, pressure_pa: float, density_kg_m3: float) -> ThermoState:
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        density = finite(density_kg_m3, "density_kg_m3", positive=True)
        if self.inverse_temperature_bounds_k is None:
            raise NotImplementedError(
                "Configure inverse_temperature_bounds_k before requesting mixture pressure-density states"
            )
        return self._invert_isobaric(pressure, density, "density_kg_m3", decreasing=True)

    def phase_viscosity(self, state: ThermoState) -> float:
        """Return a provider-reported phase viscosity; never mix component values here."""
        self.basis.require_compatible(state.basis)
        quality = getattr(state, "vapor_mole_fraction", None)
        if state.vapor_mass_fraction is not None:
            raise ValueError("Mixture viscosity requires an unambiguous native mole-quality state")
        if quality not in (None, 0., 1.):
            raise ValueError("A two-phase mixture viscosity needs a separately declared closure")
        if state.phase == "two_phase" and quality is None:
            raise ValueError("A two-phase mixture needs explicit native endpoint quality")
        if quality in (0., 1.):
            return self.saturated_phase_viscosity_pq(state.pressure_pa, quality)
        with self._lock:
            self._state.set_mole_fractions(list(self.mole_fractions))
            self._state.update(self._mixture_cp.PT_INPUTS, state.pressure_pa, state.temperature_k)
            if self._state.phase() == self._mixture_cp.iphase_twophase:
                raise ValueError("A flashed mixture requires an explicit phase-specific viscosity closure")
            return finite(self._state.viscosity(), "mixture_viscosity_pa_s", positive=True)

    def saturated_phase_viscosity_pq(self, pressure_pa: float,
                                     vapor_mole_fraction: float) -> float:
        """Query a native saturation-endpoint viscosity with explicit endpoint identity.

        The quality is CoolProp's native mole quality and only exact endpoints are
        accepted. This avoids reconstructing a saturated endpoint from PT, where
        phase identity at the saturation boundary can be ambiguous.
        """
        pressure = finite(pressure_pa, "pressure_pa", positive=True)
        quality = finite(vapor_mole_fraction, "vapor_mole_fraction")
        if quality not in (0., 1.):
            raise ValueError("Saturated phase viscosity requires native mole quality 0 or 1")
        with self._lock:
            self._state.set_mole_fractions(list(self.mole_fractions))
            self._state.update(self._mixture_cp.PQ_INPUTS, pressure, quality)
            key = self._mixture_cp.iviscosity
            method = (self._state.saturated_liquid_keyed_output if quality == 0.
                      else self._state.saturated_vapor_keyed_output)
            return finite(method(key), "saturated_mixture_phase_viscosity_pa_s", positive=True)



__all__ = ["CoolPropMixtureProperties", "MixtureThermoState"]
