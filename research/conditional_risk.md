# Native conditional single-LOC risk composition

Actual PRCT0.1.0, SciPy1.16.3; 6.8031628s.

All masses, rates, branch/occupancy assumptions, fields and receptor positions are original verification inputs. The source has declared interval masses0.0001/0.0002kg in[100,101,102]s, an actual normal-H2 HEOS state at300K/300kPa and declared isolation. This is a supplied finite mass budget, not a new release prediction. The incident40000W/m2 for5s followed byzero5s at(4,-1,1.5)m is independently supplied. No source/transport/Flame calculation produces that field here; source-to-field linkage is an explicit conditional assumption.

Actual chosen native eise/mean5 exposure probability=0.000711382704418; dose=6839903.78671(W/m2)^(4/3)s. Supplied unmeasured LOC frequency=1e-4/year, exclusive branch probabilities0.2/0.8 and conditional occupancy0.5. Actual native annual harm frequency=7.11382704418e-09/year; independent product=7.11382704418e-09/year.

Frequency is an explicit rate, not inferred from alarms, source mass or dose and not converted to annual occurrence probability. Original/owned typed native request/context, actual typed native output, native receipt, finite source and actual exposure objects are retained. Native receipt normalization is internal; no user JSON, HTTP or file interface is required. The actual direct native output is cross-checked with the native receipt. No risk equation, probit coefficient or physical source engine is duplicated.

Native/source guards reject duplicate credit, incomplete partitions, identity/provenance mismatch and replaced computed harm summaries. Native dependencies remain separate; no native source, raw process data or calibrated frequency database is bundled. This is not independent physical validation or complete facility QRA.

| Gate | Pass |
|---|---|
| actual native source/typed request/output/receipt preserved | True |
| actual exposure and native dose/probit/CDF retained | True |
| actual native risk agrees with independent explicit product below1e-20/year | True |
| all exclusive branch LOC frequencies sum to supplied rate | True |
| native reproducible receipt verification | True |
| source window and exposure support stay distinct without extension | True |
| native duplicate upstream credit rejects | True |
| native incomplete probability partition rejects | True |
| native frequency/context mismatch rejects | True |
| receptor coordinate identity mismatch rejects | True |
| physical source missing state rejects | True |
| changed computed exposure probability rejects | True |
| changed computed exposure model rejects | True |
| complete facility/physical validation claims remain false | True |
| executed source fingerprints unchanged | True |

Actual native code digest: `0d5239de3ba9a919a0a0b38a912fc86899d92f10da5e6a9e7a563d8abeec9152`; frozen dependency artifact/license receipts are in risk_dependency.toml.

| Executed host input | Begin SHA256 | End SHA256 |
|---|---|---|
| `src/h2physics/adapters/conditional_risk.py` | `bb24080cc51f3fbf3d4dd5c583aa47dfc33debc4433657bd418e624d53a12c7e` | `bb24080cc51f3fbf3d4dd5c583aa47dfc33debc4433657bd418e624d53a12c7e` |
| `tests/test_conditional_risk.py` | `6fc61b0f6523ecf8c44cd2844e3ac75269a3d51d95e435c5ee3ebb01a182fc55` | `6fc61b0f6523ecf8c44cd2844e3ac75269a3d51d95e435c5ee3ebb01a182fc55` |
| `scripts/check_conditional_risk.py` | `8303acf013b1b05e45687616bc74cafe523368d3d3939fb3ab31d798dbfcb3bd` | `8303acf013b1b05e45687616bc74cafe523368d3d3939fb3ab31d798dbfcb3bd` |
| `docs/CONDITIONAL_RISK.md` | `acd8e537627101c268bb85aedf0f4fe4f7c0343c44b8f750b7fb1f98132e8deb` | `acd8e537627101c268bb85aedf0f4fe4f7c0343c44b8f750b7fb1f98132e8deb` |
| `research/risk_dependency.toml` | `9e8bb997527c23362a60480635a65d16618c4a2242acabad2e092dce9e2ede6c` | `9e8bb997527c23362a60480635a65d16618c4a2242acabad2e092dce9e2ede6c` |
| `src/h2physics/adapters/hyram_exposure.py` | `2fbfa2ce6fea1ffade397ae75f17221dc45ef96d984137c416d05c959a7ea9cf` | `2fbfa2ce6fea1ffade397ae75f17221dc45ef96d984137c416d05c959a7ea9cf` |
| `src/h2physics/sources.py` | `856e156468b43abc609c2bdce1b01ffac5221639e970cebebe8d7c1481a5be1f` | `856e156468b43abc609c2bdce1b01ffac5221639e970cebebe8d7c1481a5be1f` |

Primary native contract: [Process Risk Consequence Toolkit](https://github.com/lyullee/process-risk-consequence-toolkit). Installed optional code is Apache-2.0; the separately used HyRAM engine is GPL-3.0-only. Public native contracts and reviewed source/notice hashes do not establish engineering qualification.
