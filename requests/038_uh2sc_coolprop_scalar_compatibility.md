# Receiving-engine request: uh2sc scalar CoolProp inputs

## Observed blocked connection

The current host path attempts an actual reviewed uh2sc calculation before binding its accepted withdrawal to compressor input. Under the local Python3.12 / CoolProp8 runtime, model initialization fails inside the existing engine. SciPy fsolve supplies a one-element pressure array; the native volume/pressure residual forwards that array through FluidWithFitOption.update into AbstractState.update, which requires scalar values. No completed native trace exists, so the host correctly refuses to fabricate a compressor handoff.

The lawful diagnostic input uses one native well control volume and an explicit numeric reservoir pressure. Earlier unsupported multiple-control-volume and string-pressure inputs are retained separately and are not the final compatibility diagnosis. No native solver source was changed.

## Requested receiving change

- Normalize a genuinely scalar or one-element native root coordinate to a scalar before invoking the native thermodynamic update. Reject non-scalar vectors with an explicit diagnostic.
- Keep the pressure, temperature and volume units, selected CoolProp backend and native conservation equations unchanged.
- Add a native-runtime compatibility test for initialization and a short finite withdrawal under the supported Python, NumPy, SciPy and CoolProp versions.
- Return an ordinary native-issued successful trace with accepted clocks, state history and withdrawal/enthalpy ledgers; do not synthesize an equivalent wrapper result.

## Host acceptance after the receiving fix

Re-run the retained underground helper in tests/test_connection_contract_equipment_storage.py, then bind the real accepted withdrawal through bind_underground_compressor_inlet. Verify original-state ownership, absolute pressure, H2 basis, mass, enthalpy and exact clock support. The host handoff must remain blocked if the native calculation fails.

## Local evidence

- artifacts/connection-contracts-20261102/equipment-frozen.xml / .log retains the scalar API failure.
- The callable underground(tmp_path) in the connection test module retains the lawful diagnostic configuration even when its known-blocked case is excluded from the healthy final batch.
- The source hashes below identify the reviewed external files; their contents are not reproduced here.

- `utilities.py` SHA-256: `2cdfde3518f69af758b3b238083e22f80d53d1a5c5813c2e9045f4f0cec0f82e`
- `fluid.py` SHA-256: `168e9629826b0cc48925f39a222ffad1bd3f25f3b271627557ab02c1c9749cca`
- `model.py` SHA-256: `e06c6b492f0a630fbe9c02e06e27854b97df7705472db7f09187bfdce83f0785`
