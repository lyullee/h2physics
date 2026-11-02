# Clashach hydrogen micro-CT/PNM source gap

## Record and rights

The candidate is [Zenodo 10.5281/zenodo.10500728](https://doi.org/10.5281/zenodo.10500728), version 2. Its record metadata explicitly declares CC BY 4.0. Dataset authors are Zaid Jangda, Hannah Menke, Andreas Busch, Sebastian Geiger, Tom Bultreys and Kamaljit Singh. The selected local source artifact is the 214,983-byte publisher `00_Readme.pdf`; its MD5 is `b824c43446213e7006f33f38ea116a87` and SHA-256 is `afede36d45a59f967647453f06c87a67e705af0d4789c039c282d03b9d84a4d9`. The large experimental PNM archives were not acquired.

## Audited schema and conditions

The README identifies `29_Pore_PNM` and `30_Throat_PNM` as 800×800×1207 voxel label images, 7 μm voxel spacing, unsigned 16-bit values. Pore labels range 1–20,980 and throat labels 1–56,126; the outside/rock region has label 0. These are image volumes rather than tabular networks with pore/throat radius, length, coordination, conductance, or permeability values.

The source describes two pore-scale hydrogen-water experiments at 50 °C and 10 MPa: hydrogen drainage enters from the sample top; brine imbibition enters from the base. README tables define image voxel coding and phase labels but do not provide a per-image clock, flow/pressure history, saturation data, capillary-pressure series, or operating-state alignment.

## Model-link decision

The current radial porous-reservoir model consumes explicit continuum cell geometry, porosity, permeability, temperature and well boundary schedules. These PNM labels do not supply those quantities or a measured flow response from which to recover them. Building a pore-network extraction/multiphase simulator would be a distinct model family, so the images are not used to claim or calibrate the current reservoir model. The two archives remain unacquired until a pore-network model and reproducible voxel-to-network workflow are implemented. See `research/data/clashach-h2-pnm-gap.toml`.
