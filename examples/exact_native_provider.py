"""Bind an application-owned native engine to an exact model-level request.

The example imports no external solver and performs no calculation. Supply the
factory from the application that owns the compatible native package.
"""

from h2physics.model_selection import ModelRegistry, ModelRequest, ProviderBinding


def register_hyram_gas_provider(registry: ModelRegistry, *, factory, revision: str,
                                evidence_ids: frozenset[str]):
    """Register one explicitly versioned high-pressure gas provider."""
    binding = ProviderBinding.bind(
        family_id="dispersion.outdoor",
        level_id="high-pressure-gas-jet",
        provider_id="hyram",
        status="implemented_unverified",
        revision=revision,
        capabilities=frozenset({"high-pressure-gas-jet", "native-result-retained"}),
        evidence_ids=evidence_ids,
        factory=factory,
    )
    return registry.register(binding)


def select_hyram_gas_provider(registry: ModelRegistry, *, evidence_ids: frozenset[str]):
    """Return a selection that admits this exact provider and evidence set."""
    return registry.select(ModelRequest(
        family_id="dispersion.outdoor",
        level_id="high-pressure-gas-jet",
        provider_id="hyram",
        accepted_statuses=frozenset({"implemented_unverified"}),
        required_capabilities=frozenset({"high-pressure-gas-jet", "native-result-retained"}),
        required_evidence_ids=evidence_ids,
    ))


__all__ = ["register_hyram_gas_provider", "select_hyram_gas_provider"]
