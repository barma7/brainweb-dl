## Why

Generated contrasts currently derive voxel values by linearly mixing tissue relaxation times from flat CSV tissue maps. This is not physically meaningful for partial-volume MRI signal behavior, and BrainWeb20 lacks proton-density/density values needed to weight tissue contributions before estimating apparent relaxation maps.

## What Changes

- Add a structured tissue-property data model that can represent canonical tissues, BrainWeb download aliases, proton-density or density weights, and field-strength-specific properties.
- Replace or augment the current CSV-only tissue map path with a JSON-backed loader suitable for BrainWeb20 and future field strengths.
- Update generated apparent relaxation maps to mix tissue signals or relaxation rates using fuzzy tissue fractions and density weights instead of linearly mixing T1/T2/T2* values.
- Provide a pragmatic apparent T2 approximation that avoids nonlinear fitting, such as an initial log-slope/rate mixture or a two-point echo-time log-slope.
- Keep native downloaded BrainWeb T1 images unchanged; this change targets generated maps derived from fuzzy segmentations.
- Non-goal: implement a full MRI sequence simulator or multi-echo nonlinear fitting engine.
- Non-goal: define authoritative tissue parameters for every field strength beyond the values shipped in the package.
- Non-goal: change BrainWeb download behavior except where alias grouping is needed to assemble canonical tissue probability maps.

## Capabilities

### New Capabilities
- `field-aware-tissue-properties`: Defines structured tissue properties, density weighting, alias mapping, and apparent relaxation-map generation from fuzzy BrainWeb segmentations.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/brainweb_dl/_brainweb.py` tissue-map loading and fuzzy alias handling; `src/brainweb_dl/mri.py` generated contrast logic; package data under `src/brainweb_dl/data/`.
- Affected public behavior: generated `T2`, `T2*`, and any future generated relaxation maps may change numerically when using the new model. Native BrainWeb T1 downloads remain unchanged.
- Affected API: likely add optional field-strength and apparent-map method parameters while preserving current defaults where practical.
- Affected tests: add focused unit tests for JSON tissue-property parsing, alias aggregation, density-weighted rate/log-slope mixing, and compatibility/error handling.
- Dependencies: no new runtime dependency is expected; use Python standard-library JSON parsing.
