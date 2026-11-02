# TU Delft H₂ core-flow storage data: rights and acquisition gap

The TU Delft ADMIRE project `H2_CT_DATA` is a potentially useful measured
storage-core source. The associated paper reports H₂/water multiphase flow in a
heterogeneous Berea sandstone core, with pressure measurements and X-ray CT
saturation observations. Its data-availability statement points to the public
[TU Delft GitLab project](https://gitlab.tudelft.nl/ADMIRE_Public/h2_ct_data).
The experiment is relevant to pore-scale storage flow only: the paper describes
100-bar laboratory work, so it does not provide pipeline, vessel-cycle, or
field-cavern operating histories.

## Repository evidence

The official GitLab project's indexed page identifies project 7511. Its file
search exposes archives such as `H2_SAT.zip`, `DRY_CORE.zip`,
`Kr_Drain_fH2_*.zip`, `Kr_Imb1_fH2_*.zip`,
`PressureData_CapillaryPressure.zip`, and `Pc_10ml_min.zip`. The official
project/API could not be fetched during this audit; consequently no byte sizes,
publisher checksums, direct asset identifiers, or internal archive schema were
confirmed.

The article itself is published under CC BY 4.0, but the inspected repository
listing does not expose an explicit license or other reuse grant for the data
archives. The article's license is not assumed to cover separately hosted data.
No archive was downloaded or copied into this repository. Revisit acquisition
only after the data repository exposes an explicit applicable reuse license and
file-level metadata.

## Relevance and limits

Potential fit is source-specific validation or characterization of core-scale
hydrogen/water pressure and saturation behavior, subject to checking test
conditions, units, channel identity, clocks, and archive integrity. This would
not establish transferability to heterogeneous field formations or cyclic
cavern injection/withdrawal. Existing acquired `hydrogen-core-flood` and
PRESLHY sources remain the immediately usable open-measurement references for
storage-core flow and cryogenic blowdown respectively; this candidate adds no
acquired evidence until its data-file rights are clear.

Audit fields and evidence URLs are recorded in
[`research/data/tudelft-h2-ct-storage-gap.toml`](../research/data/tudelft-h2-ct-storage-gap.toml).
