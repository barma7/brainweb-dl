## Why

BrainWeb20 quantitative maps can now provide PD, T1, T2, and T2* inputs, but
the package does not yet expose a small analytical layer for turning those maps
into common weighted MRI images. Users need a simple Python and CLI-compatible
API for prototype T1w, T2w, and T2*w image synthesis with a clear units
contract and explicit magnitude-noise behavior.

## What Changes

- Add a separate `synthesize_contrast.py` module for analytical contrast
  synthesis from quantitative maps.
- Add a structured Python API that accepts required quantitative maps as either
  arrays or paths and loads path inputs through existing array-loading helpers.
- Support analytical spin-echo T1w/T2w and SPGR/FLASH or GRE-style T1w/T2*w
  signal models with documented sequence-parameter units.
- Validate only the maps required by the selected contrast model.
- Add optional magnitude-image noise using Rician statistics calibrated from
  the mean clean signal in BrainWeb fuzzy white-matter voxels.
- Make stochastic noise reproducible when an RNG seed is provided.
- Add saving support for synthesized contrast results and a CLI backend that
  can consume map paths produced by the quantitative-map workflow.

## Non-Goals

- Do not implement Bloch simulation, k-space simulation, reconstruction, or
  acquisition fitting.
- Do not model coil sensitivities, coil noise correlations, or multi-coil
  noncentral-chi magnitude statistics.
- Do not add B0, B1, off-resonance, diffusion, magnetization transfer, or
  susceptibility effects in this change.
- Do not change the quantitative-map generation contract or the `get_mri()`
  download/native-MRI behavior.
- Do not provide a comprehensive preset library of vendor sequence protocols.

## Capabilities

### New Capabilities

- `analytical-contrast-synthesis`: Defines Python API and CLI-compatible
  behavior for synthesizing weighted MRI magnitude images from quantitative
  maps using simple analytical signal equations and optional WM-calibrated
  Rician noise.

### Modified Capabilities

- None.

## Impact

- Affected code: new `src/brainweb_dl/synthesize_contrast.py`; public exports
  in `src/brainweb_dl/__init__.py`; CLI parsing/entry point in
  `src/brainweb_dl/cli.py`; tests under `tests/`.
- Affected public API: add structured sequence, map, noise, result, and
  synthesis APIs. Existing APIs remain compatible.
- Affected CLI: add a contrast-synthesis command or subcommand that accepts
  quantitative-map paths, optional fuzzy segmentation for SNR calibration, and
  an output path.
- Dependencies: no new required dependency is expected beyond existing NumPy
  and NIfTI array-loading support.
