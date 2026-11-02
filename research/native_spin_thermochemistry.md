# Native pifira spin thermochemistry replay

Reproduce: `python scripts/check_pifira_spin.py` with the separately installed native targets.

pifira0.3.0; SciPy1.18.1; CoolProp8.0.0; elapsed=5.0285s. No native engine/source was modified and no printed correlation coefficients or tables were copied. All calculations are numerical verification or synthetic assumptions, not an independent measured comparison.

The native parity-resolved rotor returns rotational U relative to para J=0 and frozen-species Cv. The conversion gap is Uortho-Upara and its temperature derivative is Cvortho-Cvpara. Equal molecular masses allow the existing LH2DT para fraction to map to native c_ortho=1-x_para. These are partial spectroscopic rotor contributions, not liquid-mixture EOS, density, full fluid U/H or tank pressure. A single common reference shift applies to both branches. H mapping requires explicit no-mole-change ideal-gas or caller-evidenced spin-independent PV; no ParaHydrogen/OrthoHydrogen pure-fluid energies are subtracted.

Selected native rotor cutoff=40; reference cutoff=96; theta=85.111542192K. Native parameter fingerprint=4d9d9fd85779eb0db931de841beb281dc577c2170c1e2d0cea8272cefdd6aeab. High20000K/128-versus192-level calculation is a mathematical limit only, outside the kinetic domain and without a molecular/dense-fluid applicability claim.

| T K | Para equilibrium | Upara J/kg | Uortho J/kg | Gap J/kg | Gap derivative J/(kg K) |
|---|---:|---:|---:|---:|---:|
| 1 | 1 | 1.74417336233e-215 | 702000 | 702000 | -8.90695708308e-213 |
| 10 | 0.999999635626 | 6.98786488494e-16 | 702000 | 702000 | -3.56848774192e-15 |
| 20 | 0.998192370404 | 8.57800776593e-05 | 702000 | 701999.999914 | -0.00010951312048 |
| 40 | 0.886790311376 | 30.0539254956 | 702000.004703 | 701969.950778 | -9.58962093545 |
| 80 | 0.484734677333 | 17640.6926546 | 702196.25715 | 684555.564495 | -1369.70543589 |
| 100 | 0.385650666128 | 61898.7404565 | 703647.150049 | 641748.409593 | -2928.24199139 |
| 300 | 0.250639616101 | 1100508.01113 | 1134965.67274 | 34457.6616128 | -701.064631526 |
| 1000 | 0.250000000002 | 4006313.65512 | 4006313.65627 | 0.0011435681954 | -3.02643720715e-05 |

High-limit para fraction=0.25; Cvpara/R=1.00000040375; Cvortho/R=1.00000040375. Matched LH2DT equilibrium max difference=1.66533453694e-16.

Energy finite differences use dT=1e-4*T. Below are maximum absolute derivative errors in J/(kg K), against the native Cv and native gap derivative; this verifies actual temperature-dependent energies.

ParaCv max=1.64237605986e-05; orthoCv max=1.68321957972e-05; gap derivative max=3.29956715177e-05.

Native strict Milenko accepts liquid17-32K, gas40-120K, density up to92kg/m3 and primary ortho0.62-0.75. The public primary publisher abstract states density up to0.09g/cm3=90kg/m3; host admission conservatively caps90. This discrepancy remains explicit. Native parameter domains cannot be widened by the adapter. Phase/T/rho/composition admission is a necessary envelope screen, not validation of every combination. Frozen normal-H2 density references below retain their native property basis and an authored fixed-density composition approximation; they do not become evolving-spin EOS. Native converts kg/m3 to g/cm3 internally and its printed-rate units to1/s; no host rate formula is implemented.

| Prescribed frozen density reference | Native branch | Density kg/m3 | k_forward 1/s | Para rate at c=.7 1/s | Heat at c=.7 W |
|---|---|---:|---:|---:|---:|
| 200000Pa /17K | liquid | 74.5178003514 | 3.70812998535e-06 | 1.81666966158e-06 | 0.0255060420486 |
| 200000Pa /20K | liquid | 71.4090622751 | 3.26603311506e-06 | 1.59911418783e-06 | 0.0224515631944 |
| 2000000Pa /26K | liquid | 66.6495630861 | 2.92890390342e-06 | 1.42722287004e-06 | 0.0200382082084 |
| 2000000Pa /32K | liquid | 55.6708056581 | 2.35360552545e-06 | 1.13149070514e-06 | 0.0158861015458 |
| 100000Pa /40K | gas | 0.615497478603 | 2.45555318334e-08 | 1.13738993198e-08 | 0.000159682710914 |
| 1000000Pa /80K | gas | 3.07004881788 | 1.80579383325e-07 | 4.81737597288e-08 | 0.0006595523057 |
| 2000000Pa /100K | gas | 4.85868402473 | 3.23858768509e-07 | 5.03489431846e-08 | 0.000646227084268 |
| 1000000Pa /120K | gas | 2.01409747134 | 1.48661008229e-07 | 9.21108285892e-09 | 0.00010487365503 |

24 native rate points were executed across the eight media and three primary compositions. Dilute native density-rate ratio=2. Native reverse-threshold records count=4; their numeric table is not reproduced and does not override strict primary bounds.

Detailed-balance probing explicitly calls the native mathematical extension only after strict medium admission. It labels low-ortho values unadmitted; pure-para c=0 is an absorbing state of this native law even when thermal equilibrium c is nonzero. Zero at equilibrium and correct nearby signs do not establish a universal reverse-conversion kinetic law. No catalyst or zero-rate fallback is inferred.

The next calculation injects the actual native rate and rotor thermostat power into an external generic SciPy DOP853 verification driver. The library adds no advance, finite calorimeter ODE or trajectory API. A constant-T quadratic-law closed form provides an independent integration oracle, using native k and equilibrium without copying rate coefficients. Three driver settings(max_step/rtol)=(1000/1e-8,500/1e-10,250/1e-12)s use the absolute[100,10100]s clock, mass0.02kg, initial ortho0.7, actual frozen reference liquid density at20K/200000Pa, and an explicit rotor-bath thermostat. The path stays within the primary composition range.

Final para=0.315633539345; final external heat=-219.494892378J; max composition errors=[3.785860513971784e-14, 3.774758283725532e-14, 3.785860513971784e-14]; max delta-U-minus-Q residuals J=[np.float64(3.836930773104541e-12), np.float64(2.5295321393059567e-12), np.float64(4.064304448547773e-12)]. Analytic time to lower primary ortho boundary at these held inputs=56492.3202845s; no continuation below that boundary is admitted. No complete low-ortho long-duration storage path is predicted.

Variable-T/composition energy tangent error=1.07097997137e-10W; common-zero shift error=0J. Absolute rotor U/Cv belongs with a nonrotational sensible baseline. A full frozen EOS already contains rotational storage; callers instead request an evidenced frozen-composition correction. Identical actual/baseline composition gives zero correction. A general finite-energy driver still needs total positive heat capacity, density/phase/PV closure, strict kinetic-domain termination and a total-system energy ledger. The existing constant-gap calorimeter cannot silently accept the T-dependent native gap. It remains unchanged.

| Verification gate | Pass |
|---|---|
| actual reviewed native rotor/rate and LH2DT state used | True |
| low-T two-level equilibrium and common-ground gap | True |
| mathematical high-T 1:3 equilibrium and Cv to R | True |
| native Cv/gap derivative agree with direct energy differences | True |
| insufficient cutoff fails with actual point retained | True |
| existing LH2DT equilibrium agrees on matched theta | True |
| strict rate points use admitted actual frozen single-phase density | True |
| dilute native density-rate limit ratio two | True |
| balance probe has forward/zero/reverse signs but no admission | True |
| admitted reverse gas rate absorbs rotor energy | True |
| native92 versus primary90 density gap remains rejected | True |
| generic constant-T driver matches independent closed form | True |
| rotor thermostat delta-U equals external heat | True |
| T/composition energy tangent and common-zero invariance | True |
| identical frozen baseline correction is zero without duplicating storage | True |
| enthalpy rejected without PV evidence; explicit ideal limit retained | True |
| host and native begin/end source hashes equal | True |
| new host module/test/script/docs LF bytes | True |

Primary sources: [Petitpas2014](https://doi.org/10.1016/j.ijhydene.2014.01.205), [Milenko1997 publisher record](https://link.springer.com/article/10.1007/BF02396837), [public native source/release](https://github.com/lyullee/pifira). The existing MIT dependency review is research/pifira_dependency.toml; code/data rights are separate. No original paper, coefficient table, reverse-threshold table, experimental history or external dataset is redistributed. Experimental apparatus-transfer and dense-fluid caloric/EOS qualification remain open.

## Source fingerprints

Ordered pifira Python tree SHA256 begin=aeb729e5f3942c80d1f162523e7944954eeb3dad90fb2481fdaee021d8105c34; end=aeb729e5f3942c80d1f162523e7944954eeb3dad90fb2481fdaee021d8105c34.

New host input bytes were checked as LF-only; generated report uses explicit LF newlines.

| Host input | Begin SHA256 | End SHA256 |
|---|---|---|
| src/h2physics/adapters/pifira_spin.py | 7149a876b017349614fb777a462a7139612f57b758d67021861076bea574f88d | 7149a876b017349614fb777a462a7139612f57b758d67021861076bea574f88d |
| tests/test_pifira_spin.py | e684fce8c78b222c1d212aa9fd04b95a32fdffb1b87bd107ab98289347c696d1 | e684fce8c78b222c1d212aa9fd04b95a32fdffb1b87bd107ab98289347c696d1 |
| scripts/check_pifira_spin.py | 897555fb0ace9efd9ebcd0de7600dab71a2738ec390c921907f9c8686a52ba87 | 897555fb0ace9efd9ebcd0de7600dab71a2738ec390c921907f9c8686a52ba87 |
| docs/NATIVE_SPIN_THERMOCHEMISTRY.md | de71aea77daa577e85a8cecfff324882cf763dfddbba6efceb5b2f625ca12b20 | de71aea77daa577e85a8cecfff324882cf763dfddbba6efceb5b2f625ca12b20 |
| src/h2physics/adapters/lh2dt_spin.py | 656143c5aef02ebff24a17e9d9b6436b30ee9538baaf703d6bd00e6b7151f2a9 | 656143c5aef02ebff24a17e9d9b6436b30ee9538baaf703d6bd00e6b7151f2a9 |
| research/pifira_dependency.toml | aa86fa369ff2c7c6044bd4982efd9d5961003e59dc09595287c193fbb252dfd7 | aa86fa369ff2c7c6044bd4982efd9d5961003e59dc09595287c193fbb252dfd7 |

| Native input | Begin SHA256 | End SHA256 |
|---|---|---|
| pifira/lh2/spin.py | 0cf345f138e0fd48f213f6a0e6db668af860b64637e9fa09813e5d9896b50b6f | 0cf345f138e0fd48f213f6a0e6db668af860b64637e9fa09813e5d9896b50b6f |
| lh2dt/ortho_para.py | 479ce6744f8ffd55776759239894e8146b017045c79368e69cc17129dd5cd251 | 479ce6744f8ffd55776759239894e8146b017045c79368e69cc17129dd5cd251 |
| pifira0.3.0/LICENSE | 59ee839c628ca4c9d88fab00afa9ee1b2857caa0e6e5fe0a83c2cf9c1f68fdd4 | 59ee839c628ca4c9d88fab00afa9ee1b2857caa0e6e5fe0a83c2cf9c1f68fdd4 |
| pifira0.3.0/METADATA | 8bd164d53a130bbca68c40085589251f70611018c9c7746beaad8bfec65a3423 | 8bd164d53a130bbca68c40085589251f70611018c9c7746beaad8bfec65a3423 |
