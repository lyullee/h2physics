"""Explicit factories for the optional native HyRAM jet-radiation model."""


def build_source(*, native_packages=None, upstream_temperature_k=300.0,
                 ambient_temperature_k=293.15):
    from examples.jet_fire_conservation import build_source as build_audited_source

    source = build_audited_source(native_packages=native_packages,
                                  upstream_temperature_k=upstream_temperature_k,
                                  ambient_temperature_k=ambient_temperature_k)
    if not source.accepted:
        raise ValueError("The native HyRAM flame must pass every existing gate")
    return source


def build_policy(*, minimum_distance_m=0.25, geometry_frame_id="authored-global-z-up",
                 atmospheric_model_id="caller-transmissivity",
                 application_domain_id="steady-calm-normal-H2-air"):
    from h2physics.adapters.jet_radiation import LineRadiationPolicy

    return LineRadiationPolicy(minimum_distance_m, 1e-9, 1e-6, geometry_frame_id,
                               atmospheric_model_id, application_domain_id)
