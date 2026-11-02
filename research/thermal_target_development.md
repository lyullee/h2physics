# Thermal-target coding record

2026-10-29. Added an original finite lumped-target composition behind existing
incident-flux providers. No external prose, equation implementation or empirical
coefficient table was copied. The Stefan-Boltzmann constant is the public SI
constant; all material, geometry, optical and convective values are caller data.

The implementation deliberately reuses an original `PoolFireTrace` receptor
history by object identity. It neither copies PRCT radiation physics nor creates
a HyRAM/SLAB alternative. HyRAM remains preferred for high-pressure gas source
and exposure chains; SLABx-LH2 remains preferred for liquid-hydrogen-origin
outdoor dispersion. This target begins only after a separate owner supplies
incident heat.

Local scientific execution was prohibited for this development wave. Model
imports, example execution, validation discovery, pytest, numerical comparison
and benchmark counts are zero. Static source review only identified the four
deferred cases. They belong to a future source revision, not the pinned
`985a32a` 183-case campaign.
