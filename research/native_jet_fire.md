# Actual HyRAM+ jet-fire diagnostic replay

Reproduce: `python scripts/check_hyram_flame.py --hyram-packages artifacts/native_hyram_packages`.

HyRAM+ 6.1; SciPy 1.16.3; CoolProp 8.0.0. Four actual native Flame solves plus audits took 32.127 s. Full source-to-flame physical acceptance: **False**. The replay exits1 when physical acceptance fails, even if diagnostic verification gates pass.

All cases are original synthetic numerical inputs: normal gaseous H2 at300K, calm Air101325Pa/293.15K, Cd0.8 circular opening. Global x/y/z uses z upward; source position(0,2,2)m. A caller-declared steady established-burning premise holds on absolute clock[10,20]s; no ignition, blowdown, transient duration or frequency is computed. Native HyRAM owns the only nozzle/choking and notional-expansion solve; no shared-nozzle exit is re-choked. No engine/source field or coefficient was changed to pass an audit.

| Case | P0 Pa /d m /angle rad | Native radial points /tol | Native rows | Time s | mdot kg/s | Entry /end fuel-origin flux kg/s | Accepted |
|---|---|---|---:|---:|---:|---|---|
| coarse | 2000000 /0.002 /0 | 100 /1e-06 | 293 | 1.65765 | 0.00309566981064 | 0.00167863456267 /0.00203586905849 | False |
| fine | 2000000 /0.002 /0 | 300 /1e-07 | 776 | 5.13066 | 0.00309566981064 | 0.00167863456267 /0.00203129853092 | False |
| finest | 2000000 /0.002 /0 | 600 /1e-08 | 1728 | 15.3381 | 0.00309566981064 | 0.00167863456267 /0.0020315058065 | False |
| inclined | 20000000 /0.001 /0.78539816 | 300 /1e-07 | 877 | 7.57887 | 0.00758651852333 | 0.00377288078365 /0.00461049426639 | False |

| Native physical acceptance gate | Coarse | Fine | Finest | Inclined |
|---|---|---|---|---|
| finite positive full-visible native flame | True | True | True | True |
| native source expansion mass | True | True | True | True |
| native throat and expansion stagnation energy | True | True | True | True |
| independent section quadrature | True | True | True | True |
| direct EOS check of native combustion caloric equation | False | False | False | False |
| source to conserved fuel-origin field mass | False | False | False | False |
| conserved fuel-origin transport along flame | False | False | False | False |
| emitted radiation within native chemical-power budget | True | True | True | True |
| no native warning hidden | True | True | True | True |

The field audit independently integrates2*pi*r*rho_prod(f)*f*v dr. It uses the actual native Gaussian f/velocity widths and native reacting density. f denotes conserved fuel-origin material, including H2 bound in product water; unburned H2 is not conserved. The native ODE's last conservation row uses this same rho*f*v integrand. Splitting at actual native chemistry-table knots plus32 regular radial panels, Gauss orders8/16, and refined24-point/48-panel10B integration separates physical defects from quadrature error. Maximum8B/10B difference=8.67361737988e-19kg/s; product-based mixture-fraction check max error=4.36905484569e-08. No section has been rescaled to the nozzle flow.

| Quantity, finest case | Observed |
|---|---:|
| Source-to-field max mass defect /relative | 0.00141703524797kg/s /0.457747542422 |
| Entry-to-downstream max transport defect | 0.000352871243828kg/s |
| Throat /expansion stagnation power defect | -3.51742844942e-07 /-3.51742844942e-07W |
| Native visible length /radiant fraction | 1.04981203023m /0.0280188737897 |
| Native heat of combustion /chemical power /radiated power | 120000000J/kg /371480.377277W /10408.4618063W |
| Native radiant-power identity residual | 0W |
| Finest native warnings | () |

Native combustion uses a fixed100-point T(f) interpolation and an interpolated density derivative. The following compares its actual derivative with a central difference of its actual rho_prod(f), using df=1e-7 away from the stoichiometric kink. This diagnoses a native function inconsistency; the host does not replace that derivative or ODE.

| f | Native drho/df kg/m3 | Direct rho finite difference kg/m3 |
|---|---:|---:|
| 0.005 | -134.873343373 | -58.3986003838 |
| 0.1 | -0.154197125397 | -0.17758517469 |
| 0.4 | -0.0318568229097 | -0.0301779356365 |
| 0.8 | -0.00978860504867 | -0.0103136299501 |

The next direct-EOS audit evaluates actual native pure-fluid enthalpies at native T(f) and checks the native as-defined caloric equation. That equation multiplies reactant h by MWreactants/MWproducts before adding its heat of combustion. The unscaled mass-specific reference residual is shown separately and is not adopted as a new combustion model. Native pure-fluid zeros are not established common species formation energies. Combustion is initialized at ambient T/P, rather than the expanded cold-source state; radiation is postprocessed and does not cool the adiabatic product-temperature solution. No total radiating-flame energy closure is claimed.

| f | Native T K | Released heat J/kg | Native MW factor | Direct-EOS native-equation defect J/kg | Unscaled reference defect J/kg |
|---|---:|---:|---:|---:|---:|
| 0.005 | 740.73147853 | 600000.017858 | 0.966453512486 | -18823.770943 | -29327.6266995 |
| 0.0285209712585 | 2211.03606015 | 3422517.13208 | 0.85207115058 | -1.55311832437 | -58724.3485631 |
| 0.1 | 1410.22424216 | 3170696.73072 | 0.918892640755 | 544.205942255 | -52320.8922372 |
| 0.4 | 575.693165431 | 2113797.70966 | 0.980070213227 | 300.968592995 | -34004.2082866 |
| 0.8 | 354.531437354 | 704599.187298 | 0.996393251489 | 71.7028784885 | -11279.8716855 |

Native multisource radiation is retained only as a diagnostic of an unaccepted flame. It returns scalar incident irradiance with each emitter facing the observer, not a specified receiver-normal/absorbed wall heat flux. Native atmospheric transmission must lie in[0,1] at every path; no humidity/path/flux clipping is performed. Positive normalized-source power bounds and a far-field inverse-square limit are independent geometry/power checks, not validation of the underlying flame or radiative correlation.

Diagnostic observer points global m=[[0.0, 5.0, 2.0], [1.0, 5.0, 2.0], [1.0, -1.0, 2.0]]; irradiance W/m2=[81.43245101749518, 83.53966326741919, 83.53966326741919]. Status=diagnostic-unaccepted-flame; kernel accepted=True; whole-chain accepted=False. RH=.5; excluded emitter distance=.1m; actual min path=3.00001908346m; tau range=0.924864508876..0.927632546067. Far-field relative error=5.38643208936e-06;50/100-source difference=4.91901572426e-08.

| Diagnostic verification gate | Pass |
|---|---|
| actual native Flame objects executed | True |
| complete visible paths reached | True |
| independent order/tail quadrature agrees <1e-12 kg/s | True |
| f includes product water as conserved fuel origin, error <1e-7 | True |
| native source stagnation power audit passes | True |
| native emitted-power budgets pass | True |
| actual diagnostic radiation kernel gates pass | True |
| diagnostic radiation remains unaccepted | True |
| out-of-plane symmetry relative <1e-12 | True |
| far-field attenuated inverse-square limit relative <1e-4 | True |
| 50/100 radiation sources relative <1e-6 | True |
| native mass/caloric failures remain rejected under refinement | True |
| host/test/script/docs begin/end hashes equal | True |
| host module/test/script/docs are LF text | True |
| native source/tree/license/metadata begin/end hashes equal | True |

The existing unignited HyRAM Gaussian-jet mass failure remains separate and unchanged. This Flame evidence does not qualify a jet-fire family, heat dose, ignition/fatality model, receiver boundary, facility fire scenario or measured experiment. No independent measured comparison has been performed. Required native work includes source-matched reacting initialization, consistent rho/derivative functions, explicit caloric references and interpolation error control, and retained native solver status. Full mass/energy gates must be rerun after a reviewed revision.

Primary sources: [HyRAM+6.1 official release and manuals](https://hyram.sandia.gov/), [native6.0 technical reference](https://doi.org/10.2172/2563814), [Ekoto et al. buoyancy/radiation model](https://doi.org/10.1016/j.ijhydene.2014.03.235), [public native API/source](https://github.com/sandialabs/hyram). HyRAM+ is separately installed under GPL-3.0-only; source/coefficient tables/mechanisms/examples are not copied into these five host files. No new external dataset is downloaded or redistributed.

## Reproduction fingerprints

Host module/test/script/docs were checked as LF-only bytes. The generated report is written with explicit LF newlines.

Ordered native hyram/*.py relative-name+NUL+bytes+NUL SHA256 begin=d5865e1ae7b5c77b985e06b45d7a5607543703c1834fc50f7c5d96f32a0c22de;end=d5865e1ae7b5c77b985e06b45d7a5607543703c1834fc50f7c5d96f32a0c22de.

Native GPL COPYING.txt SHA256 begin=3237699d9e6781c85877365abd9493ca132a0fd31f43e1a3278b8e75f3654af4;end=3237699d9e6781c85877365abd9493ca132a0fd31f43e1a3278b8e75f3654af4.

Native6.1 METADATA SHA256 begin=639e1b7843a0c6a5ba92b5ca1d6e9550b5fe0db86de587bd80c9183a98a73d52;end=639e1b7843a0c6a5ba92b5ca1d6e9550b5fe0db86de587bd80c9183a98a73d52.

| Host input | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/hyram_flame.py | 3bd001f56174fccbfca6ca5ec2a882af3ffb45b656fae0f9f496b5670e7dae39 | 3bd001f56174fccbfca6ca5ec2a882af3ffb45b656fae0f9f496b5670e7dae39 |
| tests/test_hyram_flame.py | 9643c69d59d6c45bd9ef41ef0d988591facc14011e785ce9687f089a84e7247b | 9643c69d59d6c45bd9ef41ef0d988591facc14011e785ce9687f089a84e7247b |
| scripts/check_hyram_flame.py | d911843f43a1935743a5d6b7be35aee0c040ce6d71ed0d4f3ca1b2d293d2664f | d911843f43a1935743a5d6b7be35aee0c040ce6d71ed0d4f3ca1b2d293d2664f |
| docs/NATIVE_JET_FIRE.md | 5286b792c9ed79ff97f9f93527ee4d16a23bbf3f510e637e5fb6ec3e7bffce78 | 5286b792c9ed79ff97f9f93527ee4d16a23bbf3f510e637e5fb6ec3e7bffce78 |

| Native input | Begin SHA256 | End SHA256 |
|---|---|---|
| phys/_flame.py | 9a5954cdb304531ae877ce855cc3851f18fbb23d87725324c4018becdc2671d8 | 9a5954cdb304531ae877ce855cc3851f18fbb23d87725324c4018becdc2671d8 |
| phys/_jet.py | 46e80d82aee29e1912e32f626a4c04f6d390e07e7dd3398c5c28c372835301a6 | 46e80d82aee29e1912e32f626a4c04f6d390e07e7dd3398c5c28c372835301a6 |
| phys/_comps.py | 6270f56c7dc904ab4be357ba15f5b55e13b94a83f4621a204e10e21908b8ea57 | 6270f56c7dc904ab4be357ba15f5b55e13b94a83f4621a204e10e21908b8ea57 |
| phys/_therm.py | fdc042d6aa62cac4c6b99f068410bdb6e0573d1f3054caa5fa5d9fc20385840d | fdc042d6aa62cac4c6b99f068410bdb6e0573d1f3054caa5fa5d9fc20385840d |
| phys/_notional_nozzle.py | 157b1a2861b85ff1523fea1c9ccdfdc3f0bb051fe4d044652481015486abcb66 | 157b1a2861b85ff1523fea1c9ccdfdc3f0bb051fe4d044652481015486abcb66 |
| phys/_fuel_props.py | 380432a75611da0b3f66f6a4e7ea81b425b39f3ab3150ad64d584b6f2de8181f | 380432a75611da0b3f66f6a4e7ea81b425b39f3ab3150ad64d584b6f2de8181f |
