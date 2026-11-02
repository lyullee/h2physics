# Open-channel ingestion checks

Each experiment retains separate flow and sensor clock identities. Their relative
alignment is not assumed. Flow uses the source's explicit seconds and g/s columns.
The sensor clock has no unit in its header. Native concentration histories are withheld
unless the caller explicitly declares a sensor-time unit; no default seconds assumption is used.
Caller sensor-time declaration for this run: none.
Filling pressure is omitted because the column alone does not establish pressure basis.

| Experiment | Flow records | Sensor records | Invalid sensor values | Omitted padding rows |
|---|---:|---:|---:|---:|
| 23_FFI_P101_T00003 | 12167 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00004 | 17807 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00005 | 8859 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00006 | 12167 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00007 | 11732 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00008 | 12042 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00009 | 11673 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00011 | 14149 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00012 | 19411 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00013 | 19138 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00014 | 18799 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00026 | 17731 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00027 | 17753 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00028 | 19654 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00029 | 17627 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00030 | 17635 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00031 | 17347 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00040 | 30370 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00041 | 29541 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00042 | 29661 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00044 | 30518 | withheld: clock unit unresolved | — | 0 flow rows |
| 23_FFI_P101_T00045 | 31559 | withheld: clock unit unresolved | — | 0 flow rows |
