"""Native CoolProp inventories and quasi-steady Darcy links (SI units).

Install h2physics[thermo,hydraulics] for this example. The supplied friction
correlation remains replaceable. A viscosity evaluated at the declared
reference pressure/temperature is held constant along each link; this is an
explicit approximation, not a variable-viscosity transport calculation.
"""

import numpy as np

from h2physics.hydraulics import DarcyGeometry
from h2physics.isothermal_gas_pipe_network import (
    IsothermalGasPipeNetwork,
    IsothermalPipeCell,
    IsothermalPipeLink,
)
from h2physics.thermo import CoolPropIsothermalEOS, CoolPropProperties


def build_network(*, friction_law, friction_law_id):
    """Build three closed-boundary native cells with replaceable friction."""
    temperature_k = 300.
    eos = CoolPropIsothermalEOS("Hydrogen")
    properties = CoolPropProperties("Hydrogen")
    reference_pressure_pa = 9.9e6
    viscosity_pa_s = properties.state_pt(
        reference_pressure_pa, temperature_k,
    ).viscosity_pa_s
    cells = tuple(IsothermalPipeCell.from_pressure(
        cell_id=f"cell-{index}", volume_m3=.05, temperature_k=temperature_k,
        pressure_pa=pressure, eos=eos,
    ) for index, pressure in enumerate((10.e6, 9.9e6, 9.8e6)))
    geometry = DarcyGeometry(length_m=100., diameter_m=.02, roughness_m=1.e-6)
    links = tuple(IsothermalPipeLink(
        f"link-{index}", geometry, viscosity_pa_s,
    ) for index in range(2))
    return IsothermalGasPipeNetwork(cells, links, friction_law, friction_law_id)


def run_example():
    """Execute a bounded closed-inventory example using installed fluids."""
    from fluids.friction import friction_factor

    model = build_network(
        friction_law=friction_factor, friction_law_id="fluids.friction.friction_factor:default",
    )
    return model.simulate(
        boundary_mass_flow_kg_s=(0., 0., 0.),
        boundary_evidence_ids=("authored-closed-left", "authored-closed-middle", "authored-closed-right"),
        time_samples_s=np.linspace(0., .02, 5),
        minimum_cell_mass_kg=.01,
        maximum_step_s=.005,
    )


if __name__ == "__main__":
    result = run_example()
    print("Final absolute pressures [Pa]:", result.pressure_pa[-1])
    print("Maximum mass-balance residual [kg]:", np.max(np.abs(result.mass_balance_residual_kg)))
