## Context

BrainWeb20 fuzzy segmentations are 4D channel volumes on the native segmentation grid. The current tissue-property and quantitative-map pipeline interprets channel 0 as background/air, divides 12-bit fuzzy channels by 4095 independently, and uses the resulting fractions directly for T1, T2, T2*, ADC, PD, and chi maps.

The nasal air cavities are not represented correctly in the native BrainWeb20 fuzzy tissues. In practice, many nasal-cavity voxels are assigned to skull or other tissues. That is especially problematic for susceptibility because air/background uses a different chi value than skull or soft tissue.

PARASIDE can segment paranasal sinus air from a T1-weighted MRI. To keep the PARASIDE input in the same geometry as the fuzzy segmentation, the correction workflow should synthesize a T1-weighted magnitude image from quantitative maps derived from the fuzzy segmentation, then run PARASIDE on that synthesized image. Even though the fuzzy labels are wrong, the skull-like assignment in nasal cavities produces near-zero T1w signal and therefore resembles air well enough for PARASIDE to operate.

PARASIDE has a distinct dependency stack and should remain outside this package environment. The integration boundary is a subprocess call into a user-provided PARASIDE conda environment or executable.

## Goals / Non-Goals

**Goals:**

- Produce a corrected BrainWeb20 fuzzy segmentation derivative where nonzero PARASIDE mask voxels are 100% background and 0% non-background tissue.
- Preserve the raw BrainWeb native cache artifact by default.
- Keep the T1w PARASIDE input and PARASIDE output on the fuzzy segmentation grid.
- Expose both a Python API and CLI path for the end-to-end workflow.
- Provide a pure array-level patching function so the highest-risk data mutation is deterministic and easy to test.
- Record provenance sufficient to reproduce or audit the correction.

**Non-Goals:**

- Do not install, vendor, import, or depend on PARASIDE at package import time.
- Do not silently resample PARASIDE outputs or support mismatched grids in the first implementation.
- Do not change existing qmap or contrast-synthesis formulas.
- Do not interpret or preserve PARASIDE label identities in the corrected fuzzy model.
- Do not overwrite `brainweb_sXX_fuzzy.nii.gz` unless a future explicit option is designed and specified.

## Decisions

### Corrected fuzzy is a derivative, not a native cache replacement

The workflow saves a new output such as `brainweb_s04_fuzzy.nasal-air-corrected.nii.gz` plus JSON sidecar. Existing calls to `get_brainweb20(..., segmentation="fuzzy")` continue returning the raw native fuzzy file.

Alternative considered: overwrite the cache file after correction. This would make downstream qmap calls simpler but would erase the distinction between downloaded BrainWeb data and locally corrected derivatives, making provenance and reproducibility weaker.

### Use existing quantitative-map and contrast-synthesis APIs for T1w input

The workflow derives `PD_TOTAL`, `T1`, and `T2s` maps from the raw fuzzy segmentation, then synthesizes a T1w image using the existing analytical contrast API. The default SPGR/FLASH parameters are `TR=0.025 s`, `TE=0.004 s`, and flip angle `20` degrees. The nonzero TE keeps bone-like voxels dark through T2* decay, and the default input is corrupted with white-matter-calibrated Rician noise at `SNR=10` to better resemble a model input image rather than a perfectly clean synthetic map.

Alternative considered: use BrainWeb20 native T1w downloads. This was rejected because the native T1w has different resolution and uncertain subject correspondence relative to the BrainWeb20 fuzzy subjects.

### Invoke PARASIDE out-of-process

The workflow calls PARASIDE through a subprocess. Preferred command shape:

```powershell
conda run --no-capture-output -p "<paraside-env>" paraside --i "<t1w.nii.gz>" --m "<weights>"
```

The API should also allow a direct PARASIDE executable path for users who do not want to rely on `conda run`. The project Python process never imports PARASIDE modules.

Alternative considered: import PARASIDE from Python. This would give more direct control over output paths, but it would couple incompatible dependency stacks and risk contaminating this package's runtime environment.

### Treat every nonzero PARASIDE label as nasal cavity

The PARASIDE output is binarized before patching:

```text
nasal_air_mask = paraside_segmentation != 0
```

For every nonzero PARASIDE voxel, the corrected fuzzy volume sets channel 0 to `4095` for integer fuzzy data or `1.0` for normalized float fuzzy data, and all other channels to zero. This avoids depending on PARASIDE label conventions and collapses its output into one nasal-cavity mask.

Alternative considered: maintain a curated PARASIDE air-label list and ignore soft-tissue labels. This was rejected because it makes the workflow depend on PARASIDE label conventions and creates failure modes when labels change or the model emits unexpected nonzero labels.

### Validate geometry before patching

The correction requires the fuzzy spatial shape to match the PARASIDE mask shape, and path-based workflows require affines to match within numerical tolerance. Mismatches fail with a clear error.

Alternative considered: resample the mask into fuzzy space. This is deferred because label-map resampling adds orientation and interpolation choices that should be validated separately.

### Provenance sidecar is part of the output contract

The corrected fuzzy sidecar should include at minimum: source fuzzy path, output path, T1w intermediate path or retention status, PARASIDE mask path, PARASIDE command or executable mode, PARASIDE environment path or executable path, PARASIDE model path, the mask rule (`mask != 0`), number of patched voxels, affine validation status, and relevant T1w synthesis settings.

## Risks / Trade-offs

- PARASIDE may fail on some synthesized images -> Surface subprocess stderr/stdout and leave existing raw fuzzy data untouched.
- PARASIDE output naming is fixed by the external CLI -> Derive the expected output path from the input T1w filename and fail clearly if it is missing.
- T1w synthesis still depends on the flawed fuzzy model -> Accept this because skull-like nasal voxels produce low T1w signal that resembles air; keep visual QC possible by supporting retained intermediates.
- Label interpretation may change in future PARASIDE releases -> Do not interpret label identities; store the binary mask rule in provenance.
- Large BrainWeb20 volumes make extra passes expensive -> Load raw fuzzy once for qmap generation where practical, write only necessary intermediates, and apply the final patch vectorized.
- Windows path and conda behavior can be brittle -> Build subprocess arguments as a list, avoid shell string execution, and test command construction without running PARASIDE.

## Migration Plan

This is additive. Existing APIs, CLI commands, and cache files remain valid. Users opt in by running the new correction API or CLI and then passing the corrected fuzzy derivative to qmap generation.

Rollback is simply deleting or ignoring the corrected derivative and using the original BrainWeb fuzzy segmentation.

## Open Questions

- Should the CLI default to keeping T1w and PARASIDE mask intermediates, or remove the T1w image after a successful correction while always preserving the PARASIDE mask path in provenance?
