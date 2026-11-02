"""Conservative thermal-utility projection of a finite solid-reaction heat port."""

from dataclasses import dataclass
from math import fsum

from .solid_reaction_energy import inventory_enthalpy_j
from .thermal_utilities import HeatComponent, HeatSnapshot


@dataclass(frozen=True, slots=True)
class SolidReactionHeatAdapter:
    """Expose exactly prescribed reactor heat as an existing HeatDuty profile."""

    boundary_id: str = "solid-reaction-external-heat"
    identifier: str = "finite-solid-reaction-external-heat-port"

    def snapshot(self, source, window):
        from ..storage.solid_reaction import SolidReactionTrace

        if type(source) is not SolidReactionTrace:
            raise TypeError("Use the original reactor-issued SolidReactionTrace")
        rows = tuple(source.steps)
        if not rows:
            raise ValueError("Solid-reaction heat projection requires accepted steps")
        commands = tuple(row.step for row in rows)
        edges = (commands[0].start_s, *(command.end_s for command in commands))
        clock_ids = {command.clock_id for command in commands}
        if (clock_ids != {window.clock_id}
                or edges[0] != window.start_s or edges[-1] != window.end_s
                or any(left.end_s != right.start_s
                       for left, right in zip(commands[:-1], commands[1:]))):
            raise ValueError("Heat window must match the contiguous native reaction schedule")
        if (source.evidence.caloric_basis_id != source.enthalpy_provider.basis_id
                or source.kernel.energy_basis_id != source.evidence.caloric_basis_id
                or source.kernel.enthalpy is not source.enthalpy_provider):
            raise ValueError("Reaction trace changed its common enthalpy-reference basis")
        tolerance = source.kernel.tolerances
        heat = tuple(command.heat_input_j for command in commands)
        total_heat = sum(heat)
        heat_budget = tolerance.energy_j+tolerance.relative*max(
            abs(total_heat), abs(source.heat_input_j), 1.)
        if abs(total_heat-source.heat_input_j) > heat_budget:
            raise ValueError("Accepted step heat ports do not close to the trace heat ledger")
        molar_mass = {species.identifier: species.molar_mass_kg_mol
                      for species in source.species}
        initial_mass_scale = sum(source.initial.amounts_mol.get(name, 0.)*mass
                                 for name, mass in molar_mass.items())
        final_mass_scale = sum(source.final.amounts_mol.get(name, 0.)*mass
                               for name, mass in molar_mass.items())
        initial_mass_scale += sum(
            sum(supply.inventory.amounts_mol.get(name, 0.)*mass
                for name, mass in molar_mass.items())
            for supply in source.initial_supplies)
        final_mass_scale += sum(
            sum(supply.inventory.amounts_mol.get(name, 0.)*mass
                for name, mass in molar_mass.items())
            for supply in source.remaining_supplies)
        mass_budget = tolerance.mass_kg+tolerance.relative*max(
            initial_mass_scale, final_mass_scale, 1.)
        inventory_energy = lambda inventory: inventory_enthalpy_j(
            inventory, species=source.species, provider=source.enthalpy_provider,
            kernel=source.kernel,
            energy_basis_id=source.evidence.caloric_basis_id)
        initial_energy = fsum((inventory_energy(source.initial), *(inventory_energy(
            supply.inventory) for supply in source.initial_supplies)))
        final_energy = fsum((inventory_energy(source.final), *(inventory_energy(
            supply.inventory) for supply in source.remaining_supplies)))
        energy_budget = tolerance.energy_j+tolerance.relative*max(
            abs(initial_energy), abs(final_energy), abs(source.exported_enthalpy_j),
            abs(source.heat_input_j), 1.)
        amount_scale = max(
            sum(source.initial.amounts_mol.values())
            +sum(sum(supply.inventory.amounts_mol.values()) for supply in source.initial_supplies),
            1.,
        )
        element_budget = tolerance.amount_mol+tolerance.relative*amount_scale
        if (abs(source.mass_residual_kg) > mass_budget
                or abs(source.enthalpy_residual_j) > energy_budget
                or max(abs(value) for value in source.element_residual_mol) > element_budget):
            raise ValueError("Solid-reaction whole-system conservation audit is outside its budget")
        if any(not (row.before.energy_basis_id == source.evidence.caloric_basis_id
                    and row.after.energy_basis_id == source.evidence.caloric_basis_id)
               for row in rows):
            raise ValueError("Accepted reaction step changed caloric basis")
        return HeatSnapshot(
            source,
            window,
            source.evidence.process_id,
            self.boundary_id,
            source.evidence.caloric_basis_id,
            edges,
            heat,
            (HeatComponent(source.kernel, "solid-reaction.external-heat"),),
            tuple((row.before.temperature_k, row.after.temperature_k) for row in rows),
            "external-device-heat",
            (window.evidence_id, source.evidence.stoichiometry_source_id,
             source.evidence.common_temperature_assumption_id,
             source.evidence.fixed_pressure_boundary_id,
             *(command.evidence_id for command in commands)),
            (source, source.kernel, source.kinetics, source.enthalpy_provider,
             source.evidence, *rows),
            "exact caller-prescribed signed heat input; no utility availability is inferred",
        )
