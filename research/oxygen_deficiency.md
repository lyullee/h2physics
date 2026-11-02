# Native finite oxygen-room replay

Authored warm homogeneous finite inventory verification; no measured O2/human validation, LH2 condensation or cold-injury model.

Versions: {'cantera': '3.2.0', 'scipy': '1.18.1', 'numpy': '2.5.4'}. Actual local calculations: 5.77026s.

| Gate | Passed |
|---|---|
| original computed result verifies without ODE replay | True |
| replaced summary clock context and snapshot reject | True |
| current criterion fields revalidated | True |
| actual finite native reactors/networks retained | True |
| sealed O2 inventory invariant | True |
| all finite mass ledgers | True |
| all native species and O2 ledgers | True |
| all signed U-H-Q ledgers | True |
| independent native ideal P inventory identity | True |
| finite interval source masses | True |
| source native caloric enthalpy admission | True |
| independent well-mixed O2 exponential | True |
| constant-molar displacement P and T | True |
| fresh-air finite purge recovery | True |
| independent summed native UV closure | True |
| sampled crossing refinement and bracket | True |
| thermostat fraction differs from ambient pO2 | True |
| wet dry and actual partialP are distinct | True |
| actual evolving-composition shared nozzle | True |
| sampled composition admitted distinct from trial extension | True |
| original failed sources and native failure retained | True |
| no physiological or cold-injury probability | True |
| executed host/test/script/docs and native bytes unchanged | True |

```text
{
  "versions": {
    "cantera": "3.2.0",
    "scipy": "1.18.1",
    "numpy": "2.5.4"
  },
  "elapsed_s": 5.770259099997929,
  "gates": {
    "original computed result verifies without ODE replay": true,
    "replaced summary clock context and snapshot reject": true,
    "current criterion fields revalidated": true,
    "actual finite native reactors/networks retained": true,
    "sealed O2 inventory invariant": true,
    "all finite mass ledgers": true,
    "all native species and O2 ledgers": true,
    "all signed U-H-Q ledgers": true,
    "independent native ideal P inventory identity": true,
    "finite interval source masses": true,
    "source native caloric enthalpy admission": true,
    "independent well-mixed O2 exponential": true,
    "constant-molar displacement P and T": true,
    "fresh-air finite purge recovery": true,
    "independent summed native UV closure": true,
    "sampled crossing refinement and bracket": true,
    "thermostat fraction differs from ambient pO2": true,
    "wet dry and actual partialP are distinct": true,
    "actual evolving-composition shared nozzle": true,
    "sampled composition admitted distinct from trial extension": true,
    "original failed sources and native failure retained": true,
    "no physiological or cold-injury probability": true,
    "executed host/test/script/docs and native bytes unchanged": true
  },
  "host_begin_sha256": {
    "src/h2physics/adapters/oxygen_deficiency.py": "30cd0e97d3038e4054bdfe8610ce0820243610da206474fbf2d536c5033c243b",
    "tests/test_oxygen_deficiency.py": "6d2f634e3df53ea825eaf134baace52ead6090371e6cf59e8d74f1a5ccf1ed10",
    "scripts/check_oxygen_deficiency.py": "5c8303ec48ad980a2c67c5afee6b333f8e08bdce2d967ff92fad720b2b2f50ea",
    "docs/OXYGEN_DEFICIENCY.md": "0b5c59f3dc7e75ae1b6f1cab62a55db11aa8f89a06f9c8160e9f36f258e11a11",
    "src/h2physics/adapters/cantera_volume.py": "e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1",
    "src/h2physics/adapters/cantera_properties.py": "60f3d48b0b551eeec550a623ed8d2108805962204f3d465b272c78f3b918294e",
    "src/h2physics/adapters/cantera.py": "19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184",
    "src/h2physics/sources.py": "856e156468b43abc609c2bdce1b01ffac5221639e970cebebe8d7c1481a5be1f",
    "src/h2physics/core.py": "4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68",
    "src/h2physics/release.py": "eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45"
  },
  "host_end_sha256": {
    "src/h2physics/adapters/oxygen_deficiency.py": "30cd0e97d3038e4054bdfe8610ce0820243610da206474fbf2d536c5033c243b",
    "tests/test_oxygen_deficiency.py": "6d2f634e3df53ea825eaf134baace52ead6090371e6cf59e8d74f1a5ccf1ed10",
    "scripts/check_oxygen_deficiency.py": "5c8303ec48ad980a2c67c5afee6b333f8e08bdce2d967ff92fad720b2b2f50ea",
    "docs/OXYGEN_DEFICIENCY.md": "0b5c59f3dc7e75ae1b6f1cab62a55db11aa8f89a06f9c8160e9f36f258e11a11",
    "src/h2physics/adapters/cantera_volume.py": "e7079a126333183e5e2315e85f369dae197e973a7da79ab3d1a3a0010d7efce1",
    "src/h2physics/adapters/cantera_properties.py": "60f3d48b0b551eeec550a623ed8d2108805962204f3d465b272c78f3b918294e",
    "src/h2physics/adapters/cantera.py": "19d2618b0e3dd4109f938433a8e735b0783151afaeacff36ac971a2933517184",
    "src/h2physics/sources.py": "856e156468b43abc609c2bdce1b01ffac5221639e970cebebe8d7c1481a5be1f",
    "src/h2physics/core.py": "4317b90d1f60880e6c9353c17f15bda642270ec557a04d65f389499a525fdc68",
    "src/h2physics/release.py": "eba90eb0ad07209a00b29410fea9cf2018b5225533206860ea36830d1f9e3f45"
  },
  "native_begin_sha256": {
    "installed h2o2.yaml": "0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4",
    "Cantera compiled extension": "00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d",
    "Cantera license": "e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb",
    "Cantera metadata": "f483c140b917b5e758f57ac8232ece2aeb7756325801395428470a64467824c7"
  },
  "native_end_sha256": {
    "installed h2o2.yaml": "0efc6c52862741a29e0c29b65d979c7d8cb409db5282bca83b9c5437b3d8c8d4",
    "Cantera compiled extension": "00f00749cc90b76a7266656fd02e6a7d40be82e7d7e1389472ad285123064e9d",
    "Cantera license": "e92980b9712ce20e73898a97b0116889e84e07f548d6be8591e87dcad79c41bb",
    "Cantera metadata": "f483c140b917b5e758f57ac8232ece2aeb7756325801395428470a64467824c7"
  },
  "failures": {
    "unobserved source tail": {
      "error": "Finite native oxygen-room evaluation failed: An unobserved window_end tail cannot become zero flow",
      "cause": "ValueError",
      "actual_source_retained": true
    },
    "missing outside-support evidence": {
      "error": "Finite native oxygen-room evaluation failed: Declare source, region, clock, frame and evidence identities",
      "cause": "ValueError",
      "actual_source_retained": true
    },
    "arbitrary enthalpy zero": {
      "error": "Finite native oxygen-room evaluation failed: Source caloric/state mismatch: enthalpy_j_kg",
      "cause": "ValueError",
      "actual_source_retained": true
    },
    "para relabel": {
      "error": "Finite native oxygen-room evaluation failed: Property, spin-composition or energy-reference bases differ",
      "cause": "ValueError",
      "actual_source_retained": true
    },
    "cold source outside fit": {
      "error": "Finite native oxygen-room evaluation failed: Temperature is outside the mechanism domain or selected species fit bounds",
      "cause": "ValueError",
      "actual_source_retained": true
    },
    "native pressure domain": {
      "error": "Finite native oxygen-room evaluation failed: Native open-volume integration failed: \n*******************************************************************************\nCanteraError thrown by CVodesIntegrator::integrate:\nCVodes error encountered. Error code: -4\ncvHandleFailure: At t = 100.500177455482 and h = 1.69554146547895e-14, the corrector convergence test failed repeatedly or with |h| = hmin.\n\nExceptions caught during RHS evaluation:\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\n\n*******************************************************************************\nException thrown by Python callback function:\nValueError: Pressure is outside the declared mechanism domain\n*******************************************************************************\n\nComponents with largest weighted error estimates:\n0: 0\n1: 0\n2: 0\n3: 0\n4: 0\n5: 0\n6: 0\n7: 0\n8: 0\n9: 0\n*******************************************************************************\n",
      "cause": "GasVolumeIntegrationError",
      "completed_native_partitions": 1,
      "actual_network_retained": true,
      "retained_network_time_s": 100.50017745548226,
      "native_state": [
        330.6222351384314,
        1.0657825172457147,
        0.0003330050588923718,
        0.23283165801058023,
        0.7668353369305276,
        0.0
      ]
    }
  },
  "cached_result_negative_cases": {
    "cached wet summary zeros": {
      "error": "Native oxygen-result verification failed: Computed summary, clock or context differs from original native assembly",
      "supplied_retained": true,
      "actual_native_trace_retained": true
    },
    "cached dry summary zeros": {
      "error": "Native oxygen-result verification failed: Computed summary, clock or context differs from original native assembly",
      "supplied_retained": true,
      "actual_native_trace_retained": true
    },
    "cached partialP zeros": {
      "error": "Native oxygen-result verification failed: Computed summary, clock or context differs from original native assembly",
      "supplied_retained": true,
      "actual_native_trace_retained": true
    },
    "changed output clock": {
      "error": "Native oxygen-result verification failed: Computed summary, clock or context differs from original native assembly",
      "supplied_retained": true,
      "actual_native_trace_retained": true
    },
    "changed frame context": {
      "error": "Native oxygen-result verification failed: Computed summary, clock or context differs from original native assembly",
      "supplied_retained": true,
      "actual_native_trace_retained": true
    },
    "cloned snapshot object": {
      "error": "Native oxygen-result verification failed: Snapshots are not the original flattened native output prefix",
      "supplied_retained": true,
      "actual_native_trace_retained": true
    },
    "absent owner binding": {
      "error": "Native oxygen-result verification failed: Use a completed owner-built native oxygen-room result",
      "supplied_retained": true,
      "actual_native_trace_retained": true
    }
  },
  "max_defects": {
    "mass_kg": 1.893233833594188e-15,
    "all_species_kg": 1.5887794985874892e-11,
    "O2_kg": 3.700437525844258e-12,
    "U_H_Q_J": 0.00022798385282385425,
    "pressure_identity_Pa": 4.3655745685100555e-11,
    "source_mass_kg": 1.7458257062230587e-14,
    "source_enthalpy_J": 1.0222720447927713e-09,
    "analytic_O2_fraction": 1.3850032232198828e-14,
    "UV_temperature_K": 4.972093847754877e-10,
    "UV_pressure_Pa": 1.5684054233133793e-07
  },
  "mixing": {
    "final_wet_O2": 0.1719334581463828,
    "final_recovery_O2": 0.1788337515585906,
    "analytic_crossing_s": 100.3705398607686,
    "coarse_crossing_error_s": 0.0015608935512005928,
    "fine_crossing_error_s": 1.1939752269540804e-05,
    "fine_linear_duration_s": 0.6294481994791271
  },
  "shared_nozzle": {
    "actual_calls": 28,
    "max_raw_trial_sum_deviation": 1.1430543400692272e-08,
    "max_sampled_accepted_sum_deviation": 0.0,
    "signed_composition_corrections": [
      {
        "raw_sum": 0.9999999999999999,
        "species": "N2",
        "signed_mass_fraction_change": 1.1102230246251565e-16,
        "correction_id": "caller-declared-native-off-manifold-trial-extension;trial-type-unobservable"
      },
      {
        "raw_sum": 1.0000000034706178,
        "species": "N2",
        "signed_mass_fraction_change": -3.470617793155384e-09,
        "correction_id": "caller-declared-native-off-manifold-trial-extension;trial-type-unobservable"
      },
      {
        "raw_sum": 1.0000000114305434,
        "species": "N2",
        "signed_mass_fraction_change": -1.1430543400692272e-08,
        "correction_id": "caller-declared-native-off-manifold-trial-extension;trial-type-unobservable"
      }
    ]
  },
  "initial_stricter_check": "At default rtol1e-10 adiabatic U error1.00319e-5J narrowly exceeded an authored1e-5J assertion; no common budget changed. The independent UV oracle uses refined rtol1e-12/atol1e-16 above.",
  "scope": "Authored warm homogeneous finite inventory verification; no measured O2/human validation, LH2 condensation or cold-injury model."
}
```

Native failed objects are retained by OxygenRoomError during execution; this report stores diagnostic values, not serialized native engines.
Native trial type and the first hidden failing trial are unobservable through the common owner. Completed command partitions differ from hidden accepted steps.
All signed trial corrections belong only to the explicit shared-nozzle numerical extension; no negative species are clipped. Source/native caloric admission remains strict.
Installed mechanism coefficients, implementation code and outside observations are not copied into host source/distributions.
