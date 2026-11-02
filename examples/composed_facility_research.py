"""Lazy facility research builders using explicit caller-owned physical stages.

Exports ``prepare_facility_graph``, ``prepare_joint_facility_model`` and
``prepare_preferred_source_chain``. Importing or preparing a graph runs no model.
Call ``graph.run(targets=(... ,))`` or submit a joint design on the chosen execution
host when ready. Owners must supply clocks, states, openings, disposition/heat laws,
provider selection and admission evidence; the builders supply no physical defaults.
"""


def prepare_facility_graph(*, scenario_id, parameters, finite_operation,
                           source_binding, physical_stages, report_reader,
                           operation_evidence_id, source_evidence_id,
                           report_evidence_id):
    """Compose finite operation, source, ordered physical stages and reporting.

    ``finite_operation(parameters=...)`` returns the existing owner's native run.
    ``source_binding(run=...)`` must retain and admit that run's actual source.
    Each physical stage is an explicit ``(node_id, operation, evidence_id)`` tuple;
    its operation takes ``upstream=...`` and owns mass/energy/phase/clock admission.
    For example, stages may be qualified impact, native pool and preferred dispersion
    adapters. They must never infer liquid deposition merely from a liquid outlet.
    ``report_reader(upstream=...)`` returns the final caller-selected research result.
    The original outputs remain in the graph execution's named result map.
    """
    from h2physics.scenarios import (
        OperationalScenario,
        ScenarioNode,
        ScenarioOutput,
        ScenarioValue,
    )

    nodes = [
        ScenarioNode("finite-operation", finite_operation,
                     {"parameters": ScenarioValue(parameters)}, operation_evidence_id),
        ScenarioNode("source", source_binding,
                     {"run": ScenarioOutput("finite-operation")}, source_evidence_id),
    ]
    previous = "source"
    for node_id, operation, evidence_id in tuple(physical_stages):
        if node_id in {"finite-operation", "source", "report"}:
            raise ValueError("Physical stage ID conflicts with a reserved builder node")
        nodes.append(ScenarioNode(node_id, operation,
                                  {"upstream": ScenarioOutput(previous)}, evidence_id))
        previous = node_id
    nodes.append(ScenarioNode("report", report_reader,
                              {"upstream": ScenarioOutput(previous)}, report_evidence_id))
    return OperationalScenario(scenario_id, tuple(nodes))


def prepare_joint_facility_model(*, scenario_factory, output_reader, outputs,
                                 uncertainty_evidence, targets):
    """Bind scenario outputs for existing joint-input propagation without sampling.

    ``scenario_factory(physical_parameters)`` returns an OperationalScenario, such
    as ``prepare_facility_graph(...)`` with model parameters bound by its caller.
    ``output_reader(execution)`` reads original named results and returns exactly
    the declared output-variable names. Supply this returned model together with
    an explicit JointParameterSpace to ``propagate_joint`` on the execution host.
    Joint-law, transform revision and dependence evidence live in that space;
    deterministic scenario/reset evidence lives in ``uncertainty_evidence``.
    """
    from h2physics.research.joint_uncertainty import scenario_uncertain_model

    return scenario_uncertain_model(
        scenario_factory=scenario_factory, output_reader=output_reader,
        outputs=outputs, evidence=uncertainty_evidence, targets=targets,
    )


def prepare_preferred_source_chain(*, scenario_id, finite_operation, source_binding,
                                   dispersion_request, release_family, evidence_id,
                                   mass_absolute_tolerance_kg,
                                   energy_absolute_tolerance_j, gas_projection):
    """Use the domain-specific existing source-to-preferred-provider admission.

    This route requires an already resolved vapor/gas source. A declared high-pressure
    gas family selects HyRAM, and LH2 origin selects SLABx-LH2. The caller provides all
    factories, native settings and physical input evidence in ``dispersion_request``.
    A gas case also supplies its admitted HyRAM finite-window ``gas_projection``;
    pass explicit ``None`` for that argument on an LH2-origin route. The builder
    preserves provider failure and does not substitute another dispersion engine.
    """
    from h2physics.adapters.facility_accident_chain import assemble_facility_accident_chain

    return assemble_facility_accident_chain(
        scenario_id=scenario_id, finite_operation=finite_operation,
        source_binding=source_binding, dispersion_request=dispersion_request,
        release_family=release_family, evidence_id=evidence_id,
        mass_absolute_tolerance_kg=mass_absolute_tolerance_kg,
        energy_absolute_tolerance_j=energy_absolute_tolerance_j,
        gas_projection=gas_projection,
    )


__all__ = ["prepare_facility_graph", "prepare_joint_facility_model",
           "prepare_preferred_source_chain"]
