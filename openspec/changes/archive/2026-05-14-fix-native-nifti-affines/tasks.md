## 1. Affine Implementation

- [x] 1.1 Add an internal helper that builds a centered axis-aligned affine from native spatial shape and voxel resolution in millimeters.
- [x] 1.2 Update BrainWeb v1 affine selection so v1 contrasts and segmentations use the 1.0 mm native-grid affine.
- [x] 1.3 Update BrainWeb v2 T1 affine selection so native T1 uses the 1.0 mm affine derived from `T1_20_RES_SHAPE`.
- [x] 1.4 Update BrainWeb v2 crisp and fuzzy segmentation affine selection so native segmentations use the 0.5 mm affine derived from `BIG_RES_SHAPE`.
- [x] 1.5 Remove or update provisional affine TODO comments so the implementation reflects the new native affine contract.

## 2. Tests

- [x] 2.1 Add focused tests for the affine helper or affine selection covering v1 native, v2 T1, and v2 segmentation matrices.
- [x] 2.2 Add a focused save/load test confirming NIfTI files preserve the provided affine metadata.
- [x] 2.3 Add or update a generated-contrast test to verify v2 generated contrasts return the source segmentation affine when `with_affine=True`, without requiring network downloads.

## 3. Verification

- [x] 3.1 Run the repository health check with `C:\Users\marco\.conda\envs\pymarss\python.exe -m unittest discover -s tests -v`.
- [x] 3.2 Run `openspec validate fix-native-nifti-affines --strict`.
