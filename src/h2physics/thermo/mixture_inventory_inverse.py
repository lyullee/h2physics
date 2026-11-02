"""Explicit bounded frozen-mixture density/internal-energy inverse receipts."""

from dataclasses import dataclass, field


_PENDING_INVERSE_ISSUERS: set[object] = set()


def _issue_mixture_inventory_inverse(**values):
    token = object()
    _PENDING_INVERSE_ISSUERS.add(token)
    try:
        return MixtureInventoryInverse(**values, _issuer_token=token)
    except Exception:
        _PENDING_INVERSE_ISSUERS.discard(token)
        raise


class MixtureInventoryInverseError(RuntimeError):
    def __init__(self, cause, evaluations, native_root=None):
        super().__init__(str(cause))
        self.cause = cause
        self.evaluations = tuple(evaluations)
        self.native_root = native_root


@dataclass(frozen=True, slots=True)
class MixtureInventoryInverse:
    state: object
    target_density_kg_m3: float
    target_internal_energy_j_kg: float
    pressure_bounds_pa: tuple
    bracket_energy_residuals_j_kg: tuple
    evaluations: tuple
    native_root: object
    density_residual_kg_m3: float
    internal_energy_residual_j_kg: float
    branch_evidence_id: str
    monotonicity_is_sampled_only: bool = True
    _issuer_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer_token not in _PENDING_INVERSE_ISSUERS:
            raise TypeError("Create mixture inventory inverse receipts through the native provider")
        _PENDING_INVERSE_ISSUERS.remove(self._issuer_token)
