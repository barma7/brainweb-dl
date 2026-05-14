## Why

BrainWeb files saved as NIfTI should carry spatial metadata that matches the native dataset grid. The current affine handling is provisional and uses matrices that do not consistently reflect the BrainWeb v1 1 mm grid, the BrainWeb v2 0.5 mm segmentation grid, or the BrainWeb v2 1 mm T1 grid.

## What Changes

- Save native NIfTI outputs with centered, dataset-version-correct voxel-to-world affines.
- Keep BrainWeb v1 native outputs on a 1.0 mm isotropic affine.
- Keep BrainWeb v2 T1 native outputs on a 1.0 mm isotropic affine.
- Save BrainWeb v2 segmentation outputs, and generated contrasts derived from those segmentations, on a 0.5 mm isotropic affine aligned with the OpenPhantom BrainWeb convention.
- Preserve the existing public API and CLI surface; returned affines and saved NIfTI headers change, but function signatures do not.
- Non-goal: add optional BrainWeb v2 T1 resampling to the segmentation grid. That should be handled by a separate change because it changes image data, not only metadata.
- Non-goal: modify MRI contrast simulation physics, tissue maps, download aliases, or data intensity conventions.

## Capabilities

### New Capabilities
- `nifti-affines`: Defines the spatial affine contract for native BrainWeb NIfTI outputs.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/brainweb_dl/_brainweb.py` affine generation and NIfTI saving paths; possibly `src/brainweb_dl/mri.py` only where generated contrasts propagate source affines.
- Affected tests: add focused unit tests for affine generation and saved NIfTI metadata without requiring network downloads.
- Public API impact: no signature changes. Observable behavior changes for users reading `.affine` from saved NIfTI files or from `get_mri(..., with_affine=True)`.
- Dependencies: no new runtime dependencies.
