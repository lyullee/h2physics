"""Evidence-gated diagnostic comparison of cryogenic MOF rows to Langmuir H2."""

from dataclasses import dataclass, field

import numpy as np

from ..adsorption import AdsorptionBasis, ExtendedLangmuirIsotherm
from ..core import finite
from ..data.cryo_mof import CryoMOFIsothermTable

_PENDING: set[object] = set()


@dataclass(frozen=True, slots=True)
class CryoMOFLangmuirPoint:
    source_row: int
    direction: str
    pressure_pa: float
    temperature_k: float
    source_uptake_mol_kg: float
    predicted_uptake_mol_kg: float

    @property
    def uptake_residual_mol_kg(self):
        return self.predicted_uptake_mol_kg - self.source_uptake_mol_kg


def _model_signature(model):
    return (id(model), model.basis, model.domain,
            tuple(float(v) for v in model.site_capacity_mol_kg),
            model.evidence_id, id(model.affinity_pa_inv),
            id(model.affinity_temperature_derivative_pa_inv_k))


def _evaluate(table, model, direction):
    rows = table.branch(direction)
    points = []
    for row in rows:
        if row.pressure_value_si is None or row.uptake_value_si is None:
            continue
        pressure = finite(row.pressure_value_si, "source pressure", positive=True)
        uptake = finite(row.uptake_value_si, "source absolute uptake")
        if uptake < 0.:
            raise ValueError("Absolute-uptake interpretation rejects negative source values")
        state = model.equilibrium(np.asarray([pressure]), table.temperature_k)
        predicted = float(state.loadings_mol_kg[0])
        points.append(CryoMOFLangmuirPoint(row.source_row, direction, pressure,
            table.temperature_k, uptake, predicted))
    if not points:
        raise ValueError("Selected MOF source branch has no complete usable pressure/uptake rows")
    return tuple(points)


@dataclass(frozen=True, slots=True)
class CryoMOFLangmuirTrace:
    source: CryoMOFIsothermTable
    model: ExtendedLangmuirIsotherm
    direction: str
    pressure_basis_evidence_id: str
    uptake_basis_evidence_id: str
    material_identity_evidence_id: str
    points: tuple[CryoMOFLangmuirPoint, ...]
    _signature: tuple = field(repr=False, compare=False)
    _issuer: object = field(default=None, repr=False, compare=False)
    _seal: tuple = field(default=(), init=False, repr=False, compare=False)

    def __post_init__(self):
        if self._issuer not in _PENDING:
            raise TypeError("Issue MOF comparison traces through the evidence-gated adapter")
        _PENDING.remove(self._issuer)
        object.__setattr__(self, "_issuer", None)
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "_seal", self._current())

    def _current(self):
        return (id(self.source), id(self.model), self.direction,
                self.pressure_basis_evidence_id, self.uptake_basis_evidence_id,
                self.material_identity_evidence_id, self.points, self._signature)

    def require_current(self):
        self.source.require_current()
        if self._current() != self._seal:
            raise ValueError("MOF trace lost its source, model or interpretation bindings")
        if type(self.model) is not ExtendedLangmuirIsotherm or _model_signature(self.model) != self._signature:
            raise ValueError("The exact Langmuir model owner or parameters changed")
        if self.points != _evaluate(self.source, self.model, self.direction):
            raise ValueError("MOF model outputs no longer reproduce from the retained owners")
        return self


def compare_cryo_mof_with_langmuir(source: CryoMOFIsothermTable,
        model: ExtendedLangmuirIsotherm, *, direction: str,
        pressure_basis_evidence_id: str, uptake_basis_evidence_id: str,
        material_identity_evidence_id: str) -> CryoMOFLangmuirTrace:
    """Evaluate exact 77/87 K source points; do not fit or extrapolate.

    The source reports a bar pressure coordinate but does not settle absolute
    versus relative pressure. Its mmol/g uptake does not settle excess versus
    absolute uptake or material-mass basis. This bridge requires caller evidence
    for each interpretation and for material identity. 20 K reference-volume
    rows are excluded because their denominator state is unresolved.
    """
    if type(source) is not CryoMOFIsothermTable or type(model) is not ExtendedLangmuirIsotherm:
        raise TypeError("Supply the issued MOF source table and existing Langmuir model")
    source.require_current()
    for value, label in (
        (pressure_basis_evidence_id, "absolute-pressure interpretation"),
        (uptake_basis_evidence_id, "absolute-uptake/mass-basis interpretation"),
        (material_identity_evidence_id, "source material identity"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Caller evidence for {label} is required")
    if source.temperature_k not in {77., 87.}:
        raise ValueError("Only 77/87 K reported-bar, mol/kg branches are eligible for this bridge")
    if (source.pressure_quantity != "reported_pressure" or source.pressure_source_unit != "bar"
            or source.pressure_si_unit != "Pa" or source.uptake_quantity != "specific_amount"
            or source.uptake_source_unit != "mmol/g" or source.uptake_si_unit != "mol/kg"):
        raise ValueError("Source schema is outside the reviewed 77/87 K pressure/uptake contract")
    if (model.basis.species != ("H2",) or model.basis.loading_definition != "absolute"
            or model.basis.material_id != source.material_label):
        raise ValueError("Model must use source-matched material identity, H2 and absolute uptake")
    if direction not in {"adsorption", "desorption"}:
        raise ValueError("Choose one source-ordered adsorption or desorption branch")
    signature = _model_signature(model)
    points = _evaluate(source, model, direction)
    token = object()
    _PENDING.add(token)
    try:
        return CryoMOFLangmuirTrace(source, model, direction,
            pressure_basis_evidence_id.strip(), uptake_basis_evidence_id.strip(),
            material_identity_evidence_id.strip(), points, signature, _issuer=token)
    except Exception:
        _PENDING.discard(token)
        raise
