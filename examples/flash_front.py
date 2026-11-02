"""Authored premixed material-lattice reference; unexecuted coding example."""


def build_reference(*, width_m=.04, slope=.08):
    import hashlib
    from pathlib import Path

    import cantera as ct

    from h2physics.adapters.cantera import CanteraGas, FlameSettings, MechanismBasis, ReactiveState
    from h2physics.adapters.flash_front import FrontAdmission, premixed_reference

    raw = (Path(ct.__file__).parent/"data"/"h2o2.yaml").read_bytes()
    basis = MechanismBasis("installed-Cantera-h2o2:ohmech", hashlib.sha256(raw).hexdigest(),
        "Cantera-BSD-3-Clause;upstream-GRI-Mech-provenance",
        ("https://cantera.org/3.2/examples/input/h2o2.html",), 300., 3500., 1e4, 2e6)
    owner = CanteraGas.from_yaml(raw, basis, phase_name="ohmech")
    total = 6.76
    mixture = ReactiveState(310., 101325., {"H2": 2/total, "O2": 1/total, "N2": 3.76/total})
    native = owner.free_flame(mixture, FlameSettings(width_m, refinement_slope=slope))
    admission = FrontAdmission("authored-quiescent-material-reference", "initial-material-lattice",
        "authored-clock", "authored-stoichiometric-H2-air", "numerical-reference-not-field-qualified",
        .1, .9, 500., .005, .02, 1e-8)
    return premixed_reference("native-h2-air", owner, native, admission)


def run_example():
    from h2physics.adapters.flash_front import FrontCell, MaterialContact, run_material_front

    reference = build_reference()
    cells = tuple(FrontCell(f"cell-{i}", (i, 0, 0), reference) for i in range(5))
    return run_material_front(cells, spacing_m=(.1, .1, .1), ignition_cell_ids=("cell-0",),
        ignition_s=10., horizon_s=11., clock_projection_tolerance_s=1e-10, contacts=(
            MaterialContact("material-marker", "cell-2", 10., 11., "authored-material-occupancy"),))
