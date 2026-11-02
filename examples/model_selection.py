"""Authored model-selection objects; this example is not executed locally."""

from h2physics.model_selection import ModelRegistry, ModelRequest, ProviderBinding


def authored_factory(*, label):
    return {"selected_model": label}


def build_registry():
    registry = ModelRegistry()
    registry.register(ProviderBinding.bind(
        family_id="dispersion.outdoor",
        level_id="high-pressure-gas-jet",
        provider_id="HyRAM+",
        status="native_adapter_verified",
        revision="application-pinned-revision",
        capabilities={"high-pressure-gas", "native-dispersion"},
        evidence_ids={"application-dependency-receipt", "application-domain-evidence"},
        factory=authored_factory,
    ))
    return registry


def explicit_selection(registry=None):
    registry = build_registry() if registry is None else registry
    return registry.select(ModelRequest(
        family_id="dispersion.outdoor",
        level_id="high-pressure-gas-jet",
        provider_id="HyRAM+",
        accepted_statuses={"native_adapter_verified"},
        required_capabilities={"high-pressure-gas"},
        required_evidence_ids={"application-dependency-receipt"},
    ))


def main():
    built = explicit_selection().build(label="authored-demo")
    print(built.selection.binding.provider_id, built.model)


if __name__ == "__main__":
    main()
