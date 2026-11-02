# Reliquefier product to native separator liquid inlet

`bind_reliquefier_product_to_separator()` projects an owner-issued
`ReliquefierProductReceipt` into the existing LH2DT finite separator's
phase-specific `phase_flows` callback. It admits only collected product that
the reliquefier collector already classified as all liquid, checks the exact
target hydrogen property basis, and computes one constant mass rate from the
receipt's collected mass and declared product window. Each callback returns a
native liquid `MassEnergyFlow` carrying the receipt product state's specific
enthalpy.

The caller must assign the collection window to the tank operation clock,
identify the target liquid receiver region, and provide evidence for the
transfer boundary's pressure and thermal feasibility. The callback rejects
times outside that exact window, revalidates the source
receipt on every evaluation, and preserves its clock, product state and mass
accounting. The deferred contract checks out-of-window calls and rejection of
missing transfer-boundary identity. The handoff does not infer liquid-line hydraulics, pressure drop,
flashing, thermal conditioning, phase change in transit, or tank response. The
native separator remains responsible for its own phase inventory, wall/heat
balances, pressure response and accepted-state accounting.

Deferred Hangang contract: `reliquefier-product-native-separator-liquid-inlet-handoff`
under the existing `finite-transfer` profile. Its authored synthetic coupling
checks interface accounting only; it is not an experiment, apparatus
qualification, or evidence for transfer-line behavior.
