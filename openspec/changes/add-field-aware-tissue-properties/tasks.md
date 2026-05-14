## 1. Data Model

- [ ] 1.1 Add a structured BrainWeb20 tissue-property JSON file with canonical tissues, aliases, density values, supported field strengths, units, and per-field properties.
- [ ] 1.2 Add a loader that validates required metadata fields and normalizes properties into arrays aligned with canonical tissue order.
- [ ] 1.3 Preserve or document the migration path from the existing CSV tissue maps.

## 2. Fuzzy Tissue Handling

- [ ] 2.1 Add alias aggregation so multiple BrainWeb fuzzy channels can contribute to one canonical tissue.
- [ ] 2.2 Add tests for canonical tissue aggregation, including grouped fat-related aliases.

## 3. Apparent Relaxation Generation

- [ ] 3.1 Replace linear generated relaxation-time mixing with density-weighted relaxation-rate or signal-based apparent-map generation.
- [ ] 3.2 Implement an initial-slope method for fast apparent T2/T2* generation.
- [ ] 3.3 Consider a two-point echo-time method for acquisition-aware apparent T2/T2* generation.
- [ ] 3.4 Define and test behavior for background-only or zero-density voxels.

## 4. Public API and Documentation

- [ ] 4.1 Decide default field strength and expose any needed optional parameters without disrupting native T1 loading.
- [ ] 4.2 Update docstrings and README text to describe generated maps as apparent approximations.
- [ ] 4.3 Add compatibility notes for changed generated contrast values.

## 5. Verification

- [ ] 5.1 Add focused unit tests for metadata parsing, alias aggregation, density weighting, and apparent-map math.
- [ ] 5.2 Run the repository health check with `C:\Users\marco\.conda\envs\pymarss\python.exe -m unittest discover -s tests -v`.
- [ ] 5.3 Run `openspec validate add-field-aware-tissue-properties --strict`.
