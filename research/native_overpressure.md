# Native conditional unconfined peak overpressure

Authored mathematical/native interface verification only. Participating hydrogen mass, combustion heat, ambient absolute pressure and blast centre are explicit supplied evidence. No release/flammable/detonable cloud field, ignition or detonation probability is inferred. The existing rejected HyRAM Gaussian-entry source remains rejected; this API never accepts a Jet.

The actual public Bauwens_method.calc_scaled_overpressure_from_dist static function owns all correlation coefficients/values. No fabricated Jet, cloud, native instance or copied table is used. Host dimensional definitions are E=m_H2*q, Rstar=R*(Pambient/E)^(1/3), deltaP=Pambient*Pstar. There is no inferred efficiency, TNT substitution or ground/reflection multiplier.

Original synthetic envelope: participating H2 mass0.001/0.01/0.08kg, q120MJ/kg; ambient80/100/120kPa absolute; 81 scaled distances1–100 per pair; physical standoff>=0.1m. The coefficient, participation and envelope inputs are not experimental/calibrated values. Event snapshot100s uses its declared operation clock; no arrival-time or waveform is solved.

## Actual native runtime checks

| SciPy | NumPy | HyRAM | Local calculation s | Gates passed |
|---|---|---|---:|---:|
| 1.16.3 | 2.5.4 | 6.1 | 0.012483 | 12/12 |
| 1.18.1 | 2.5.4 | 6.1 | 0.012603 | 12/12 |

No native ODE is executed in this standalone route. Passing both runtimes does not resolve the separate full-Jet SciPy callback/source failures.

| Participating H2 kg | Ambient absolute Pa | Energy J | R at Rstar1 m | deltaP at Rstar1 Pa | deltaP at Rstar100 Pa |
|---:|---:|---:|---:|---:|---:|
| 0.001 | 80000 | 120000 | 1.14471424255 | 32424 | 59.0968875689 |
| 0.001 | 100000 | 120000 | 1.06265856918 | 40530 | 73.8711094611 |
| 0.001 | 120000 | 120000 | 1 | 48636 | 88.6453313533 |
| 0.01 | 80000 | 1200000 | 2.46621207433 | 32424 | 59.0968875689 |
| 0.01 | 100000 | 1200000 | 2.28942848511 | 40530 | 73.8711094611 |
| 0.01 | 120000 | 1200000 | 2.15443469003 | 48636 | 88.6453313533 |
| 0.08 | 80000 | 9600000 | 4.93242414866 | 32424 | 59.0968875689 |
| 0.08 | 100000 | 9600000 | 4.57885697021 | 40530 | 73.8711094611 |
| 0.08 | 120000 | 9600000 | 4.30886938006 | 48636 | 88.6453313533 |

Maximum published anchor error: 5.55111512313e-17; mass/ambient similarity defect: 5.55111512313e-17.

10kPa threshold radii for0.01/0.08kg: [6.141727866490636, 12.283455732981272]m. Maximum native forward pressure defect: 1.81898940355e-12Pa; root-refinement radius difference: 3.04910336979e-08m.

Native mathematical far-field exponent at Rstar1e9/2e9: -1.33333343068; this is outside the application envelope and is a mathematical limit only. Zero participating mass calls the actual native static function at Rstar=infinity and returns zero. That explicit zero-energy limit does not create a finite cloud or an impulse estimate.

Cross-runtime anchor pressure difference: 0Pa.

| Gate | Compatible runtime | Host runtime |
|---|---|---|
| actual standalone native class/function retained; no Jet instantiated | True | True |
| 729 participating-mass/ambient/distance points equal native raw correlation | True | True |
| independent published unit-scaled-distance anchor error <2e-15 | True | True |
| all nine positive-energy pressure profiles strictly decrease | True | True |
| mass/ambient dimensional similarity defect <2e-15 | True | True |
| eightfold participating energy doubles threshold radius <1e-12 m | True | True |
| native inverse forward-pressure error <1e-7 Pa | True | True |
| root-tolerance refinement radius difference <1e-7 m | True | True |
| native infinite-scaled-distance zero-energy limit returns zero pressure | True | True |
| independent mathematical far-field exponent tends to -4/3 <1e-6 | True | True |
| domain/frame/unbracketed cases reject without clamping | True | True |
| all native source/license/metadata begin/end fingerprints unchanged | True | True |

## Retained domain failures

| Attempt | Actual error |
|---|---|
| near-origin Rstar0.001 | Receptor standoff is below the explicitly declared physical domain |
| outside ambient P | Ambient absolute pressure is outside the declared domain |
| unbracketed target | Target pressure is not bracketed within the declared scaled-distance domain |
| wrong frame | Receptors and event centre must share the declared coordinate frame |

## Full native constructors and receiving boundary

- `Bauwens_method(jet_object, heat_of_combustion=None, min_streamline_divisions=50, number_radial_divisions=50, max_cell_gradient=0.1, minimum_number_detonable_cell=5, origin_at_orifice=False)`
- `TNT_method(jet_object, equivalence_factor, heat_of_combustion=None, flammability_limits=None, origin_at_orifice=False)`
- `BST_method(jet_object, mach_flame_speed, heat_of_combustion=None, flammability_limits=None, origin_at_orifice=False)`

All three full constructors consume a real Jet: TNT/BST call its flammable-mass integration and determine an origin from its concentration field unless explicitly overridden; Bauwens also discretizes the real jet, evaluates cell-size/gradient criteria and integrates participating fuel. The inspected high-level compute_overpressure likewise constructs a Jet. They cannot accept the currently rejected source as a qualified cloud. Only the actual standalone Bauwens pressure correlation is executed here. TNT's separate static equivalent-mass function exists, but no TNT/BST pressure-table route is advertised by this adapter.

Receiving work: native explicit participating-energy/mass constructors with provenance; separate immutable field-inventory/source audits; explicit pressure/geometry/domain and point-source/reflection conventions. Full source-to-cloud coupling remains blocked by the recorded Gaussian mass gap. No receiving project was edited or contacted.

No impulse, positive-phase duration, waveform, reflection, enclosure/obstacle amplification, DDT/initiation or annual frequency is returned. The pressure rise is relative to ambient; ambient-plus-rise is labeled separately. Threshold radius is a conditional inversion, not a qualified safe/separation distance. No apparatus or field validation is inferred.

Primary sources: [Sandia HyRAM technical reference](https://www.osti.gov/servlets/purl/2563814), [Bauwens and Dorofeev ICHS2019, pressure/energy/distance definitions onp10](https://hysafe.info/uploads/papers/2019/279.pdf), [native public source](https://github.com/sandialabs/hyram). HyRAM6.1 is separately installed GPL-3.0-only; no native code, coefficient tables or external measurements are bundled. Mathematical anchors and original scaling tests are not measured validation.

## Begin/end fingerprints

| Native bytes | Begin SHA256 | End SHA256 |
|---|---|---|
| ordered-native-Python | d5865e1ae7b5c77b985e06b45d7a5607543703c1834fc50f7c5d96f32a0c22de | d5865e1ae7b5c77b985e06b45d7a5607543703c1834fc50f7c5d96f32a0c22de |
| _unconfined_overpressure.py | 98efd60479f4eb58f41c6a568887e5f4df938e2d0a6cb475c206b7bd098ba865 | 98efd60479f4eb58f41c6a568887e5f4df938e2d0a6cb475c206b7bd098ba865 |
| _overpressure_data.py | 9985714e8255284e6a4110de4e683f778f268512fc4a0bab588da138007ff3a3 | 9985714e8255284e6a4110de4e683f778f268512fc4a0bab588da138007ff3a3 |
| GPL-COPYING.txt | 3237699d9e6781c85877365abd9493ca132a0fd31f43e1a3278b8e75f3654af4 | 3237699d9e6781c85877365abd9493ca132a0fd31f43e1a3278b8e75f3654af4 |
| native-METADATA | 639e1b7843a0c6a5ba92b5ca1d6e9550b5fe0db86de587bd80c9183a98a73d52 | 639e1b7843a0c6a5ba92b5ca1d6e9550b5fe0db86de587bd80c9183a98a73d52 |

| Host source/test/replay | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/hyram_overpressure.py | 0f219090615b3e42c582f3c6b4abe72d350ff92651ea5c0e696d02c5e671c5a6 | 0f219090615b3e42c582f3c6b4abe72d350ff92651ea5c0e696d02c5e671c5a6 |
| tests/test_hyram_overpressure.py | 5ceafb43bf8d7e3a3c500916c75853f3212199b35a4dc2e51eaf464dadb582e7 | 5ceafb43bf8d7e3a3c500916c75853f3212199b35a4dc2e51eaf464dadb582e7 |
| scripts/check_hyram_overpressure.py | 57c2a64d2511fded611ccc6e934d23e989607e88a5c7eb5668eebfbce8359d33 | 57c2a64d2511fded611ccc6e934d23e989607e88a5c7eb5668eebfbce8359d33 |
| src/h2physics/core.py | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 | 4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68 |

Host/native source-byte guards passed: True. Cross-runtime gate: True.
