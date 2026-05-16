## Why

BrainWeb20 fuzzy segmentations do not explicitly model the nasal air cavities, causing many nasal-cavity voxels to be represented as skull or other tissues. This biases susceptibility and downstream B0-map evaluations because those voxels should behave as air/background rather than tissue.

## What Changes

- Add a nasal-air correction workflow for BrainWeb20 fuzzy segmentations.
- Synthesize a T1-weighted image on the native fuzzy-segmentation grid to provide PARASIDE with same-resolution anatomical input.
- Run PARASIDE as an external process from its dedicated conda environment so the project environment remains isolated from PARASIDE dependencies.
- Patch a BrainWeb20 fuzzy segmentation by treating every nonzero PARASIDE segmentation voxel as nasal cavity, setting those voxels to 100% background and all non-background tissue channels to zero.
- Save the corrected fuzzy segmentation as a derivative artifact with provenance metadata rather than overwriting the native BrainWeb cache artifact by default.
- Expose Python API and CLI entry points for the workflow, plus a pure mask-patching function for deterministic testing.
- Non-goals:
  - Do not vendor PARASIDE or add its dependencies to this package.
  - Do not replace BrainWeb native fuzzy downloads or silently change `get_brainweb20(..., segmentation="fuzzy")`.
  - Do not resample mismatched PARASIDE outputs in the first implementation; shape or affine mismatches should fail explicitly.
  - Do not change the physical tissue-property model beyond assigning selected nasal-air voxels to the existing background/air channel.

## Capabilities

### New Capabilities

- `nasal-air-correction`: Correct BrainWeb20 fuzzy segmentations with PARASIDE-derived nasal-air masks and save corrected derivative outputs with provenance.

### Modified Capabilities

- None.

## Impact

- Affected code:
  - New correction module for T1w intermediate generation, PARASIDE invocation, mask loading, fuzzy patching, validation, and provenance.
  - CLI additions, likely a new `brainweb-dl-nasal-air-correct` console script.
  - Public package exports for the Python correction API and pure patching helper.
  - Focused tests for command construction, mask patching semantics, validation failures, output naming, and CLI/API behavior.
- Public API:
  - Add `correct_fuzzy_nasal_air(...)` for end-to-end correction.
  - Add `patch_fuzzy_with_air_mask(...)` for deterministic array-level patching.
- External dependency:
  - PARASIDE remains optional and external. The workflow calls a user-provided conda environment or executable path through a subprocess.
- Compatibility:
  - No breaking changes. Existing BrainWeb downloads, qmap generation, analytical contrast synthesis, and cache behavior remain unchanged unless callers explicitly use the corrected derivative.
