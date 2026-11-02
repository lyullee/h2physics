"""Measurement-based electrocatalyst metrics with explicit charge and site bases.

No fit window is selected automatically. A straight Tafel region and a large
R-squared do not by themselves identify a mechanism or remove transport effects.
Scientific context: https://doi.org/10.1038/s41598-021-87951-z
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import trapezoid

from .constants import FARADAY_C_MOL, R_J_MOL_K
from .core import _real_numeric_array, finite, immutable_array


def _vector(value, name):
    vector = _real_numeric_array(value, name)
    if vector.ndim != 1 or not len(vector) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a nonempty finite vector")
    return vector


def corrected_overpotential_v(measured_potential_v, equilibrium_potential_v, current_a, *,
                               remaining_uncompensated_resistance_ohm):
    """Return signed E-Eeq-I*R using resistance still present in the observations.

    Currents are signed (anodic positive). If the instrument already compensates
    part of the resistance, pass only the remaining resistance to avoid applying
    compensation twice. Potentials must share one reference electrode scale.
    """
    resistance = finite(remaining_uncompensated_resistance_ohm, "remaining resistance")
    if resistance < 0:
        raise ValueError("Remaining uncompensated resistance must be nonnegative")
    values = [_real_numeric_array(v, n) for v, n in
              ((measured_potential_v, "potential"), (equilibrium_potential_v, "equilibrium"),
               (current_a, "current"))]
    try:
        measured, equilibrium, current = np.broadcast_arrays(*values)
    except ValueError as exc:
        raise ValueError("Potential and current arrays must broadcast") from exc
    if not all(np.all(np.isfinite(v)) for v in (measured, equilibrium, current)):
        raise ValueError("Potential and current inputs must be finite")
    with np.errstate(over="ignore", invalid="ignore"):
        result = measured-equilibrium-current*resistance
    if not np.all(np.isfinite(result)):
        raise ValueError("Corrected overpotential exceeds finite numeric range")
    return float(result) if result.ndim == 0 else immutable_array(result)


@dataclass(frozen=True, slots=True)
class TafelFit:
    slope_v_decade: float
    intercept_v_at_1_a_m2: float
    exchange_current_density_a_m2: float
    covariance: np.ndarray
    selected_indices: np.ndarray
    residual_v: np.ndarray
    r_squared: float
    branch: str
    area_basis: str
    protocol_id: str
    current_density_window_a_m2: tuple[float, float]

    def __post_init__(self):
        for name in ("covariance", "selected_indices", "residual_v"):
            object.__setattr__(self, name, immutable_array(getattr(self, name)))

    def transfer_coefficient_times_electrons(self, temperature_k):
        """Return alpha*n_eff; the overall 2e/4e product stoichiometry is separate."""
        temperature = finite(temperature_k, "temperature", positive=True)
        return finite(math.log(10)*R_J_MOL_K*temperature/(
            FARADAY_C_MOL*self.slope_v_decade), "fitted transfer coefficient times electrons")


def fit_tafel(overpotential_v, current_density_a_m2, *, branch: str, area_basis: str,
              protocol_id: str, current_density_window_a_m2: tuple[float, float],
              overpotential_standard_uncertainty_v=None) -> TafelFit:
    """Fit |eta| = a + b*log10(|j|/(1 A/m2)) within a caller-declared window.

    Cathodic inputs must have negative current and negative overpotential;
    anodic inputs must have positive signs. Values outside the fit window may
    belong to other regimes. Standard uncertainties, when supplied, describe
    independent voltage errors only; current error/correlation is not modeled.
    Covariance order is intercept, slope. j0 is a model extrapolation.
    """
    eta = _vector(overpotential_v, "overpotential")
    current = _vector(current_density_a_m2, "current density")
    if current.shape != eta.shape:
        raise ValueError("Current and overpotential samples must align")
    if branch not in {"anodic", "cathodic"} or area_basis not in {"geometric", "ECSA"}:
        raise ValueError("Declare anodic/cathodic branch and geometric/ECSA area basis")
    if not isinstance(protocol_id, str) or not protocol_id.strip():
        raise ValueError("Measurement and fit-window protocol identity is required")
    if len(current_density_window_a_m2) != 2:
        raise ValueError("Declare lower and upper absolute-current fit bounds")
    lower, upper = (finite(x, "fit bound", positive=True) for x in current_density_window_a_m2)
    if lower >= upper:
        raise ValueError("Fit window must have increasing positive bounds")
    sign = 1 if branch == "anodic" else -1
    selected = np.flatnonzero((np.abs(current) >= lower) & (np.abs(current) <= upper))
    if len(selected) < 3:
        raise ValueError("At least three samples in the declared fit window are required")
    if np.any(sign*current[selected] <= 0) or np.any(sign*eta[selected] <= 0):
        raise ValueError("Selected samples must belong to the declared kinetic branch")
    x = np.log10(np.abs(current[selected]))
    y = sign*eta[selected]
    if np.ptp(x) < 1e-6 or np.ptp(y) == 0:
        raise ValueError("Fit needs a resolved nonconstant log-current and voltage span")
    if overpotential_standard_uncertainty_v is None:
        sigma = np.ones_like(x)
    else:
        uncertainty = _vector(overpotential_standard_uncertainty_v, "voltage uncertainty")
        if uncertainty.shape != eta.shape or np.any(uncertainty <= 0):
            raise ValueError("Positive voltage uncertainties must align with all samples")
        sigma = uncertainty[selected]
    # Center the predictor before solving to reduce intercept/slope conditioning.
    center = float(np.mean(x))
    design = np.column_stack([np.ones(len(x)), x-center])
    weighted_design, weighted_y = design/sigma[:, None], y/sigma
    beta, _, rank, _ = np.linalg.lstsq(weighted_design, weighted_y, rcond=None)
    if rank != 2 or beta[1] <= 0:
        raise ValueError("A positive identifiable Tafel slope is required")
    slope = float(beta[1])
    intercept = float(beta[0]-slope*center)
    residual = y-(intercept+slope*x)
    covariance_centered = np.linalg.inv(weighted_design.T@weighted_design)
    if overpotential_standard_uncertainty_v is None:
        covariance_centered *= float(residual@residual)/(len(x)-2)
    transform = np.array([[1., -center], [0., 1.]])
    covariance = transform@covariance_centered@transform.T
    log_j0 = -intercept/slope
    if not -300 < log_j0 < 300:
        raise ValueError("Extrapolated exchange current is outside representable research range")
    r_squared = 1-float(residual@residual)/float(np.sum((y-np.mean(y))**2))
    return TafelFit(slope, intercept, 10.**log_j0, covariance, selected, residual,
                    r_squared, branch, area_basis, protocol_id, (lower, upper))


@dataclass(frozen=True, slots=True)
class ProductChargeComparison:
    product: str
    electrons_per_product_molecule: int
    interval_edges_s: np.ndarray
    product_mol: np.ndarray
    charge_magnitude_c: np.ndarray
    faradaic_efficiency: np.ndarray
    clock_id: str
    measurement_id: str

    def __post_init__(self):
        for name in ("interval_edges_s", "product_mol", "charge_magnitude_c", "faradaic_efficiency"):
            object.__setattr__(self, name, immutable_array(getattr(self, name)))


def compare_product_to_charge(current_time_s, current_a, *, interval_edges_s, product_mol,
                              product: str, current_clock_id: str, collection_clock_id: str,
                              measurement_id: str) -> ProductChargeComparison:
    """Compare collected H2 (2e) or O2 (4e) with time-aligned electrode charge.

    Product is the amount collected in each interval, already corrected for any
    independently known collection losses/transport delay. Current magnitude is
    integrated piecewise-linearly without extrapolation. Polarity reversal is
    rejected: forward and reverse reaction intervals must be analyzed separately.
    Efficiencies > 1 are retained as a measurement/balance diagnostic, not clipped.
    """
    time = _vector(current_time_s, "current time")
    current = _vector(current_a, "current")
    edges = _vector(interval_edges_s, "collection interval edges")
    amount = _vector(product_mol, "collected product")
    if (len(time) < 2 or time.shape != current.shape or np.any(np.diff(time) <= 0)
            or len(edges) < 2 or np.any(np.diff(edges) <= 0) or time[0] < 0
            or amount.shape != (len(edges)-1,) or np.any(amount < 0)
            or edges[0] < time[0] or edges[-1] > time[-1]):
        raise ValueError("Collection intervals and nonnegative product must lie within current support")
    for identity in (current_clock_id, collection_clock_id, measurement_id):
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError("Clock and measurement identities must be explicit")
    if current_clock_id != collection_clock_id:
        raise ValueError("Align current and collection clocks before charge comparison")
    if product not in {"H2", "O2"}:
        raise ValueError("This measurement API supports H2 or O2 product stoichiometry")
    electrons = 2 if product == "H2" else 4
    charges = []
    for start, end in zip(edges[:-1], edges[1:], strict=True):
        knots = np.r_[start, time[(time > start) & (time < end)], end]
        values = np.interp(knots, time, current)
        if np.any(values > 0) and np.any(values < 0):
            raise ValueError("Reaction polarity reverses within a collection interval")
        charge = finite(abs(float(trapezoid(values, knots))), "integrated charge")
        if charge <= 0:
            raise ValueError("A zero-charge interval has no defined Faradaic efficiency")
        charges.append(charge)
    charges = np.asarray(charges)
    with np.errstate(over="ignore", invalid="ignore"):
        efficiency = electrons*FARADAY_C_MOL*amount/charges
    if not np.all(np.isfinite(efficiency)):
        raise ValueError("Faradaic efficiency exceeds finite numeric range")
    return ProductChargeComparison(product, electrons, edges, amount, charges, efficiency,
                                    current_clock_id, measurement_id)


def turnover_frequency_from_product(product_rate_mol_s: float, *, active_site_amount_mol: float,
                                     site_basis_id: str) -> float:
    """Moles product/(moles counted active sites*s), requiring an explicit site basis."""
    rate = finite(product_rate_mol_s, "product rate")
    sites = finite(active_site_amount_mol, "active site amount", positive=True)
    if rate < 0 or not isinstance(site_basis_id, str) or not site_basis_id.strip():
        raise ValueError("Declare nonnegative product rate and the independently counted active sites")
    return finite(rate/sites, "turnover frequency")


def turnover_frequency_from_current(current_a: float, *, product: str,
                                    faradaic_efficiency: float, active_site_amount_mol: float,
                                    site_basis_id: str) -> float:
    """Convert charge with declared FE; product electron count is not a Tafel parameter."""
    if product not in {"H2", "O2"}:
        raise ValueError("Declare H2 or O2 product")
    efficiency = finite(faradaic_efficiency, "Faradaic efficiency")
    if not 0 <= efficiency <= 1:
        raise ValueError("Predictive current-to-product conversion requires FE in [0, 1]")
    rate = abs(finite(current_a, "current"))*efficiency/(
        (2 if product == "H2" else 4)*FARADAY_C_MOL)
    return turnover_frequency_from_product(rate, active_site_amount_mol=active_site_amount_mol,
                                           site_basis_id=site_basis_id)
