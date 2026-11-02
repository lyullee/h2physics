# Native pressure-relief integration

Reproduce: `python scripts/check_relief_integration.py` after separately installing the reviewed native snapshot.

Native source revision `b2f276333c1b1793c39f25763703d196d36742ec`, separately installed MIT LH2DT; HEOS through the existing single-flash facade; CoolProp 8.0.0, SciPy 1.18.1; 35.8024 s local calculation wall time. Six integrations include three temporal refinements, zero heat, sealed heating and a finite inventory floor.

Original synthetic gas case: normal H2, V=0.01 m3; fluid/wall initially 300 K; initial upstream 190000 Pa absolute; wall capacity 100 J/K; ambient/fluid-wall UAs 1/10 W/K. Set/reseat 200000/180000 Pa absolute are caller inputs. Fixed downstream 100000 Pa, effective-area factor 1, opening 1e-6 m2. A manufactured explicit wall boundary gives constant net 100 W after accounting for the native ambient UA. Clock [100,130] s; maximum steps 0.5/0.25/0.125 s. This is a finite homogeneous gas reference, not a vapor pickup model for a stratified cryogenic tank or a rated relief device.

Native PressureReliefValve.evaluate mutates its latch on trial calls. The retained raw test has band flow 0 kg/s before a high-pressure trial and 0.000117234071427 kg/s afterwards. Protected trials call the actual underlying native Valve subclass at the fixed accepted opening; only its public evaluate method delegates the existing shared valve/nozzle. A native latch copy is promoted only after successful accepted-event evaluation. No protected latch field, native equation or external source is edited.

Native HomogeneousTank.simulate owns each RK4 interval and boundary ledger. Host event replay starts from the same accepted tank/latch state and brackets the first resolved threshold. Endpoint detection does not establish completeness for arbitrary unresolved within-step nonmonotonic pressure excursions. The maximum step and forcing bandwidth need independent convergence/application checks.

| Quantity | Observed value |
|---|---:|
| Fine open event | 119.611409917 s; 200000.000003 Pa |
| Fine reseat event | 120.690429859 s; 179999.999931 Pa |
| Fine released mass / stagnation enthalpy | 0.00012361375957 kg / 510.682719466 J |
| Maximum mass / fluid+wall energy defect | 2.03287907341e-19 kg / 2.88764567813e-11 J |
| Maximum threshold pressure / clock-bracket error | 6.91761088092e-05 Pa / 7.45058059692e-09 s |
| Coarse/medium event-time differences from fine | [7.692724466323853e-05, 3.7923455238342285e-06] s |
| Coarse/medium released-mass differences from fine | [7.893556409151094e-09, 3.884198050273669e-10] kg |
| Coarse/medium final pressure differences from fine | [1.0864905815396924, 0.05347291918587871] Pa |
| Fine accepted-sample mass / enthalpy quadrature differences | 1.68710552972e-09 kg / 0.0206786424187 J |
| Fine accepted/trial native intervals | 241 / 289 |
| Positive inventory-floor time / mass | 100.131608479 s / 0.0016781483329 kg |

| Gate | Pass |
|---|---|
| actual native tank/relief/Valve and native valve-result objects retained | True |
| raw native evaluation-order failure reproduced, protected probes remain closed | True |
| three resolutions agree on open/reseat cycle | True |
| native event pressure error <=0.001 Pa and clock bracket <=1e-8 s | True |
| closed finite mass / fluid+wall energy defects <1e-12 kg /1e-5 J | True |
| independent constant net wall heat integrates exactly to 3000 J | True |
| zero-heat closed analytic limit | True |
| sealed positive-heat analytic total-U change 100 J | True |
| event times / released mass / final pressure refine <0.01 s /1e-7 kg /10 Pa | True |
| finest independent accepted-sample mass/enthalpy quadrature <0.01% | True |
| positive inventory floor localized, without fake valve isolation | True |
| original accepted-native origins were not mutated by integration | True |
| begin/end native and host fingerprints unchanged | True |

Pressure actuation uses physical upstream absolute pressure, not a transmitter reading or a differential-pressure substitution. Event pre/post source limits remain separate at the same tank state and clock. The remote throttling port retains upstream enthalpy; the one solved nozzle plane retains static enthalpy plus KE. The current native homogeneous tank owns bulk-mixture withdrawal. No unknown vapor takeoff, vent-stack backpressure, area, heat load, actuator stroke or annual initiating frequency is inferred.

These are numerical/interface verification results. Native binary hysteresis excludes manufacturer lift curves, seat leakage, finite stroke, chatter mechanics and certification. Equal set/reseat and downstream at/above reseat are explicitly unavailable at this event level. Native failures and sub-floor clock intervals fail with accepted tank/protection state retained, rather than becoming successful isolation. Further receiving work is a public native latch snapshot/restore/pure-evaluate interface, native accepted-event hooks and general first-crossing/dense-output capability. No receiving repository was changed or messaged.

Primary sources: [native LH2DT](https://github.com/lyullee/lh2dt_models), [NASA Glenn choking reference](https://www.grc.nasa.gov/www/k-12/airplane/mflchk.html), [ANL cryogenic relief thermodynamic context](https://www.phy.anl.gov/division/esh/Cryogenic/Appendix%202/appendix%202.htm). The adapter/event driver/tests are original; no valve/tank implementation, coefficient table or experimental dataset is bundled. This replay is not relief sizing, certification or vendor qualification.

## Begin/end fingerprints

- Native Python aggregate before: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`
- Native Python aggregate after: `5406adc4092bfad5c9d4671874951999a9e5f83ee2ffafaf823bb1a6bf2e3e61`
- Native `tank.py`: `b921a604a9ee27b87db41737964bfe9ea111bc66a1a0ee7a237c646fba385c22`
- Native `valve.py`: `042c9cf014d78e69a0bc59982fcf4ac8752c657572b4d9e3371cd3e22c28d9e0`
- Native `properties.py`: `835f694d46c55882dc9b51bdeda714995c05eda4bd90b3055662fb06ae6293a3`
- Native `streams.py`: `047dcfe84dbe25d44a2ba9f66f6a88a0b4f27827cd64d681569ef0c6cd3e02ca`
- Native `adaptive.py`: `3040ac0501bbdd8bcca3cade84ee13b20de560679a8561f5607ebff7c6f29491`
- `src/h2physics/adapters/lh2dt_relief.py`: `4bc8eedc38819c46fface826f294863ecfd0fa1fefd53191a4bb77d8105b5282`
- `tests/test_lh2dt_relief.py`: `f5f8e6e0b59eb9964585c552b43f732a3f08b0e124f9c7f98955707ba36fda8d`
- `scripts/check_relief_integration.py`: `2e06d7c61f7784da3bce0580ceb84c4f31da4f85e95b40721ce0318e06fba866`
- `src/h2physics/adapters/lh2dt_equipment.py`: `87c29e0b47f35da3e38baf4ca2ce1832f58a91104701a95c144e5e30f7080b33`
- `src/h2physics/release.py`: `eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45`
- `src/h2physics/adapters/lh2dt_properties.py`: `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2`
- Native unchanged: True; host source/test/script unchanged: True.

| Host source | Begin SHA-256 | End SHA-256 |
|---|---|---|
| `src/h2physics/adapters/lh2dt_relief.py` | `4bc8eedc38819c46fface826f294863ecfd0fa1fefd53191a4bb77d8105b5282` | `4bc8eedc38819c46fface826f294863ecfd0fa1fefd53191a4bb77d8105b5282` |
| `tests/test_lh2dt_relief.py` | `f5f8e6e0b59eb9964585c552b43f732a3f08b0e124f9c7f98955707ba36fda8d` | `f5f8e6e0b59eb9964585c552b43f732a3f08b0e124f9c7f98955707ba36fda8d` |
| `scripts/check_relief_integration.py` | `2e06d7c61f7784da3bce0580ceb84c4f31da4f85e95b40721ce0318e06fba866` | `2e06d7c61f7784da3bce0580ceb84c4f31da4f85e95b40721ce0318e06fba866` |
| `src/h2physics/adapters/lh2dt_equipment.py` | `87c29e0b47f35da3e38baf4ca2ce1832f58a91104701a95c144e5e30f7080b33` | `87c29e0b47f35da3e38baf4ca2ce1832f58a91104701a95c144e5e30f7080b33` |
| `src/h2physics/release.py` | `eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45` | `eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45` |
| `src/h2physics/adapters/lh2dt_properties.py` | `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2` | `818fb98b5d2084107c072f62c8e00f9b4d7df36f6044db2af8f3b82f0f6910c2` |
