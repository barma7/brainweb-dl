## Context

`brainweb-dl` downloads raw BrainWeb arrays and saves them as NIfTI files through helper functions in `src/brainweb_dl/_brainweb.py`. The current affine helper is hard-coded per download alias and still carries a provisional TODO. Some matrices do not match the native grid expected for BrainWeb v1, BrainWeb v2 T1, or BrainWeb v2 segmentations.

The OpenPhantom BrainWeb code uses a centered 0.5 mm affine for BrainWeb v2 segmentation data. This change adopts the same centering convention while preserving `brainweb-dl`'s current array layout and NIfTI last row convention.

## Goals / Non-Goals

**Goals:**
- Save native NIfTI files with axis-aligned, centered affines expressed in millimeters.
- Use 1.0 mm isotropic voxels for BrainWeb v1 native files.
- Use 1.0 mm isotropic voxels for BrainWeb v2 T1 native files.
- Use 0.5 mm isotropic voxels for BrainWeb v2 segmentation files and generated contrasts derived from v2 segmentations.
- Preserve API and CLI signatures.
- Cover the affine contract with focused tests that do not require network access.

**Non-Goals:**
- Resample BrainWeb v2 T1 images to the segmentation grid.
- Change image orientation, axis order, raw download aliases, tissue labels, tissue maps, or intensity scaling.
- Change generated MRI contrast physics or randomization behavior.
- Introduce Python/Numba simulator parity work; this package change does not touch a simulator backend.

## Decisions

### Use a shape-and-resolution affine helper

Implement a small internal helper that builds a centered affine from a native shape and isotropic voxel size:

```text
affine[:3, :3] = diag(resolution_mm)
affine[:3, 3] = -0.5 * shape[:3] * resolution_mm
affine[3, 3] = 1
```

This yields the OpenPhantom v2 segmentation translation `(-90.5, -108.5, -90.5)` for shape `(362, 434, 362)` at 0.5 mm, while also giving the matching centered v1 translation for shape `(181, 217, 181)` at 1.0 mm.

Alternative considered: keep per-alias hard-coded matrices. That preserves local structure but makes future shape or resolution fixes easier to get wrong and obscures the shared centering rule.

### Keep native products on native grids

BrainWeb v2 T1 remains a 1.0 mm native product. The affine for v2 T1 should be derived from `T1_20_RES_SHAPE` and `STD_RES_MM`, not from the v2 segmentation resolution. Optional T1-to-segmentation resampling is deferred to a separate change because it changes image data and user-visible shapes.

Alternative considered: treat all v2 outputs as 0.5 mm. That would be wrong for v2 T1 because BrainWeb distributes that product on a 1.0 mm grid.

### Propagate source affines for generated contrasts

Generated contrasts such as v2 T2* are computed from fuzzy segmentations. They should continue to read and return the affine from the source segmentation NIfTI, which will become the corrected 0.5 mm segmentation affine after this change.

Alternative considered: recompute generated contrast affines independently. That duplicates logic and risks divergence from the saved segmentation source.

### Preserve `.npy` behavior

`.npy` outputs do not carry affine metadata. Existing `load_array()` identity-affine behavior for `.npy` files remains unchanged.

## Risks / Trade-offs

- Existing cached NIfTI files with old affines will not be rewritten unless callers use `force=True` or delete the cached file. Mitigation: document in implementation notes and tests that the new affine applies when files are saved.
- Users comparing exact affines may observe changed metadata. Mitigation: no function signatures change, and the new values are the intended native spatial metadata.
- Centering assumes the current stored array axis order remains unchanged. Mitigation: this change does not alter reshape, transpose, or orientation behavior; it only corrects voxel size and origin metadata for the current layout.
