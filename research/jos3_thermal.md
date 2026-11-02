# Native ordinary-air multisegment thermal response

Actual pythermalcomfort4.7.0/NumPy2.5.4; enabled native JIT, 4.43488930s.

The authored subject and environment are numerical verification inputs, not a clinical cohort. An actual prepared native JOS3 object is copied without changing its definition/state. Native neutral-setpoint initialization retains only its final native output; its hidden warmup trajectory is unavailable. Ordinary-air10C for300s followed by25C for300s uses supplied clothing/activity and an explicit101325Pa model reference. No H2-rich convection, cryogenic contact/boiling, freezing, respiratory injury, hypoxia or physiological damage law is introduced.

Native JOS3 owns85 capacities/nodes,17 local body segments, physiology and implicit stepping. Original native models, rounded native outputs, unrounded native body temperatures, absolute/elapsed clocks and failure-prefix objects survive. The source prepared model is unchanged. Historical snapshots are separate from mutable returned native objects.

The original native displayed sensible heat uses the previous skin temperature. Its integrator uses the implicit updated skin temperature with the beginning-state native dry resistance/operative temperature. The audit queries those native properties before each step, then independently compares native capacity times temperature change with the actual implicit boundary. The native output is never rewritten to hide that difference. Native total thermogenesis/respiration and17latent powers are rounded0.01W; their worst-case summed precision is0.095W times step duration, plus the declared1e-6J numerical budget. This is a rounding bound, not an adjustable physical heat correction.

10/5/2.5s final-node refinement differencesK: [0.008112454238073497, 0.004025068906514662]; maximum step storage/boundary defectsJ: [0.43019558495704757, 0.2249433732873456, 0.10819019364037885].

The native previous-shivering global limiter is not isolated across models. It is explicitly rejected when enabled; no global state or native equations are patched. The native unused shivering option cannot mean disabled physiology. Custom native hc/hr or ex_q require another audited boundary and are rejected at this level. Original NUMBA_DISABLE_JIT=1 import failed with a native compilation/dispatcher AttributeError; enabled native JIT succeeds. The factory rejects the disabled profile without a substitute engine. This record establishes numerical/API limits only; independent human validation and source/environment applicability remain open.

| Gate | Pass |
|---|---|
| actual native copied model and original owner retained | True |
| original prepared state and neutral output unchanged | True |
| all original returned native step outputs retained | True |
| explicit 85 capacities and17 local skin/core states | True |
| exact direct unmodified native campaign | True |
| exact independently declared command edge | True |
| native clock is elapsed and absolute offset retained | True |
| all storage and implicit heat audits within output precision | True |
| total native stored energy equals sum of step changes | True |
| reported old-state sensible heat differs from implicit boundary | True |
| native time refinement contracts | True |
| all three rejected native boundaries retain cause and actual model | True |
| body-domain rejection retains native completed output | True |
| no injury probability or validated cryogenic chain inferred | True |
| executed inputs unchanged | True |

| Rejected original case | Cause | Completed host-admitted steps | Native elapsed s |
|---|---|---:|---:|
| hidden-shivering-rate-memory | ValueError: Native global previous-shivering rate limiter is outside the isolated campaign level | 0 | 0.0 |
| custom-heat-source | ValueError: Custom native heat coefficients/ex_q need a separately audited energy boundary | 0 | 0.0 |
| body-domain | ValueError: Native body temperatures exceed the declared nonfreezing thermal domain | 0 | 10.0 |

Native94 Python-file aggregate SHA256: `84eb0b8ccd6d7aba575a3949ff27bc6bfe4485e33ee3e467cc5b57b0237c8d18`.

| Host input | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/jos3_thermal.py | 83e675554ac3dc2fd100c0de02dbd7860656293c11c38a18a92070c43a9a7c49 | 83e675554ac3dc2fd100c0de02dbd7860656293c11c38a18a92070c43a9a7c49 |
| tests/test_jos3_thermal.py | 98751bb03a6c04e362a104bedb4ccbccdd9f060408ce0ac563907c33705fe6ac | 98751bb03a6c04e362a104bedb4ccbccdd9f060408ce0ac563907c33705fe6ac |
| scripts/check_jos3_thermal.py | bc4aa6d4008832c95cab05510b996dfbc89201cfc78c68549f4e27d7791e9839 | bc4aa6d4008832c95cab05510b996dfbc89201cfc78c68549f4e27d7791e9839 |
| docs/JOS3_THERMAL.md | a5b80175f5541c51b0b832d51c368c082059e764c39be610d0cdeba7742a5f02 | a5b80175f5541c51b0b832d51c368c082059e764c39be610d0cdeba7742a5f02 |
| research/thermal_dependency.toml | 95146dd34aacc93ba2daaee41f672b9b218f9dfded436916212b86b18b279234 | 95146dd34aacc93ba2daaee41f672b9b218f9dfded436916212b86b18b279234 |

Primary sources: [native4.7.0 metadata](https://pypi.org/project/pythermalcomfort/4.7.0/), [actual native documentation](https://pythermalcomfort.readthedocs.io/en/latest/documentation/models.html), [native source/license](https://github.com/pythermalcomfort/pythermalcomfort), [original model bibliographic record](https://doi.org/10.1016/j.enbuild.2020.110575). The publisher full-text endpoint returned403; no full original validation dataset was inspected or redistributed. MIT/native dependency notices and exact artifact hashes are in thermal_dependency.toml. No native source/coefficient table is bundled.
