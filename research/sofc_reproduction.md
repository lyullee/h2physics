# Open SOFC curve reproduction

Source: [Mendeley dataset v1](https://doi.org/10.17632/j8b9v4cb9d.1), CC BY 4.0. Source filename: `Ui_50H2_10H2O_40N2.txt`. Source SHA-256: `eac5c114ecec8747169dd2f260a599a8f8fdcaeddcea8856ab1fd44161cf4e33`.

Voltage origin remains unresolved (the collection includes model/experimental material). This is explicitly curve reproduction, not independent experimental parameter estimation or qualification. The observation operator reuses the local symmetric Butler–Volmer and ohmic loss classes. An affine open-circuit-like temperature term and activated resistance are fitted; these effective coefficients are not assigned to a particular electrode mechanism or standard reaction energy.

The 800 °C curve is held out in full. Curves at 750, 775 and 825 °C are used for fitting. They share an apparatus/source, so group separation is not independent-source validation. Residual normalization is 0.01 V for numerical scaling; it is not a measured uncertainty. The illustrative target, selected in the script before fitting, is RMSE ≤0.02 V and maximum absolute error ≤0.05 V.

- Fitting observations: 1854; omitted invalid rows: 0.
- Fitting data fingerprint: `30d20c2be4b8b64e1cec3f23566a9db9e6162bd23e06d7d9a91b9cfff1021129`.
- Held-out observations: 618; fingerprint: `a08da31fd7e8782cde16ee66bfd9d3f990e9ecd7420ea5f4ee88b7824ce01a46`.
- Fitting RMSE: 0.00543444421 V.
- Held-out RMSE: 0.00607121488 V.
- Held-out maximum absolute error: 0.0200204512 V.
- Illustrative reproduction target: PASS.
- Scaled Jacobian rank: 5/5 at relative threshold 1e-08.
- Scaled Jacobian condition number: 40907.4755.
- Scaled singular values: (5234.566451148124, 1367.3837094009818, 137.3635919915667, 20.76086817056557, 0.12796112158710984).

| Effective parameter | Fitted value | Declared lower / upper | Active bound |
|---|---:|---|---:|
| reversible_like_v | 1.010665566 | 0.2 / 1.8 | 0 |
| temperature_coefficient_v_k | -0.00020313723 | -0.005 / 0.005 | 0 |
| resistance_ohm_m2 | 4.102977086e-05 | 1e-08 / 0.001 | 0 |
| resistance_activation_j_mol | 29683.11918 | 0 / 100000 | 0 |
| exchange_a_m2 | 36241.3838 | 0.01 / 1e+07 | 0 |

The open-circuit-like coefficient is not a qualified reversible voltage. No covariance or confidence interval is inferred from fitting residuals. Inspect rank, conditioning and active bounds before interpreting fitted coefficients. True thermochemistry, gas activities, observation origin and an independent source are still required for physical electrochemical validation.
