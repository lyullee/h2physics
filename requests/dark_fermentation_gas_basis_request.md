# Dark-fermentation gas measurement and reactor-state request

Prepared request for Roberto Hernández and the Mendeley record maintainers for
[Raw data v2](https://doi.org/10.17632/2nwcdx9hst.2), CC BY 4.0. Not sent. The
165,296-byte workbook is acquired and its source columns are read; this request
seeks missing physical definitions before any reported gas trace is compared with
the existing `QsdSanAdm1Digester` model.

For each reactor/run and time row, please provide a versioned sidecar keyed to the
workbook's exact worksheet row and `Nr` identifier with:

1. BP gas-volume basis: actual or standard volume, reference pressure and temperature,
   dry/wet basis, gas collection apparatus, flow-meter method, calibration/blank
   correction, sampling window and averaging procedure.
2. For CO2/CH4/H2, whether the values are volume or mole fractions, which species are
   included in the denominator, and the exact sampling/averaging times aligned to BP.
3. Define the basis and measured status of HP/MP, HY, HPR/MPR; identify whether these
   are computed from BP/fractions, the denominator mass for yield/productivity, and
   any volume or mass normalization. Retain the known worksheet row 239 (source Nr
   241) HP/MP discrepancy as a source issue rather than silently correcting it.
4. Duration clock origin, sampling schedule/cadence, batch-day or elapsed-day meaning,
   and matching times for feed, withdrawal, pH, COD and gas sampling. Identify any
   repeated/decreasing duration rows and provide the original event log.
5. Per-reactor liquid working volume, headspace volume, operating temperature,
   mixing and gas vent/backpressure boundaries.
6. Initial substrate and COD quantities, glucose/pig-manure feed composition and
   feeding histories, biomass/inoculum concentration and inventory, gas-liquid
   transfer/collection details, and pH control or alkali-addition history.
7. Clarify whether R1/R2/R3 are independent biological replicates, repeated stages,
   or reactors with shared inputs; provide run-specific operating conditions.
8. Provide measurement uncertainty or calibration records and exact file version/hash
   for any sidecar. Confirm the CC BY 4.0 grant also covers the new materials.

The existing source has a `Duration` column in days, but the project preserves its
relative reported coordinate and does not infer event time or cadence. It records BP
as reported gas-volume rate, not a standard-volume gas molar flow. Do not substitute
ideal-gas conversion or derive missing process states from the workbook's algebraic
columns. A source-bounded observation operator can be considered after the sidecar
resolves these semantics; no kinetics fit is requested.
