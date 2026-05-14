## 1. Data Model

- [x] 1.1 Add a strict BrainWeb20 tissue-property JSON file with channel names, labels, aliases, proton density, ADC, chi, field-aware relaxation mean/std values, units, and provisional markers.
- [x] 1.2 Add a JSON loader/validator that normalizes properties into channel-aligned structures.
- [x] 1.3 Keep existing CSV files as deprecated historical package data.

## 2. BrainWeb20 Fuzzy Channel Handling

- [x] 2.1 Update BrainWeb20 fuzzy download assembly to use JSON channel aliases instead of CSV rows.
- [x] 2.2 Add logging for missing known channels and errors for unexpected extra channels in qmap generation.

## 3. Quantitative Map Generation

- [x] 3.1 Add a `QuantitativeMapResult` dataclass and `get_quantitative_map()` API.
- [x] 3.2 Implement raw fuzzy conversion as per-channel `raw / 4095` without per-voxel renormalization.
- [x] 3.3 Implement `VF`, `VF_TOTAL`, `PD`, and `PD_TOTAL` outputs.
- [x] 3.4 Implement deterministic apparent `T1`, `T2`, and `T2s` maps using proton-density-weighted rate estimates and second-unit outputs.
- [x] 3.5 Implement `ADC` and `chi` maps using the agreed weighted models.
- [x] 3.6 Implement optional reproducible stochastic relaxation sampling with positive-value clipping.

## 4. Persistence and CLI

- [x] 4.1 Add NIfTI plus JSON sidecar saving for quantitative-map results.
- [x] 4.2 Add HDF5 saving for one or more quantitative-map results.
- [x] 4.3 Add `brainweb-dl-qmap` CLI with `--property`, `--field-strength`, `--output`, `--stochastic`, and `--rng` options.
- [x] 4.4 Update package entry points and public exports.

## 5. Documentation

- [x] 5.1 Update README/docs to describe quantitative maps, units, no-renormalization behavior, and approximation limits.
- [x] 5.2 Document the CSV deprecation and BrainWeb20-only qmap scope.

## 6. Verification

- [x] 6.1 Add focused tests for JSON parsing, fuzzy fraction conversion, qmap math, stochastic reproducibility, persistence metadata, and CLI behavior.
- [x] 6.2 Run the repository health check with `C:\Users\marco\.conda\envs\pymarss\python.exe -m unittest discover -s tests -v`.
- [x] 6.3 Run `openspec validate add-field-aware-tissue-properties --strict`.
