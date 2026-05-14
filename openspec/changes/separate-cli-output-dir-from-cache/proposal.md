## Why

The CLI currently treats `--brainweb-dir` inconsistently: segmentation commands save into that directory, while contrast commands also write a second exported file into the current working directory. The Python API also has a v2 path where `brainweb_dir` is not propagated for segmentations and generated contrasts, which can silently read or write the default cache instead of the caller-provided directory.

## What Changes

- Add an explicit CLI output destination for all requested products, covering T1/T2/T2*/PD-style contrasts and crisp/fuzzy segmentations.
- Keep `--brainweb-dir` as the BrainWeb native-data cache/download directory rather than the final export destination.
- Make CLI output behavior consistent: the requested output is written under the explicit output destination for every supported contrast/segmentation.
- Preserve cache behavior for native BrainWeb files unless a later change introduces a no-cache mode.
- Fix Python API `brainweb_dir` propagation so v2 segmentation and generated-contrast paths consistently use the caller-provided directory.
- Document compatibility behavior for users who currently rely on `--brainweb-dir` as the segmentation output directory.
- Non-goal: implement a no-cache/in-memory-only download mode.
- Non-goal: resample BrainWeb v2 T1 to the segmentation grid.
- Non-goal: change affine metadata, tissue maps, image intensity conventions, or generated contrast physics.

## Capabilities

### New Capabilities
- `cli-output-routing`: Defines how CLI commands choose final output paths independently from the BrainWeb cache directory.
- `python-cache-directory-consistency`: Defines the Python API contract for consistently honoring `brainweb_dir` across native downloads, segmentations, and generated contrasts.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/brainweb_dl/cli.py`, `src/brainweb_dl/mri.py`, and possibly download helpers in `src/brainweb_dl/_brainweb.py` if an output-copy helper is needed.
- Public CLI impact: introduces a new explicit output option and standardizes where final outputs are saved. Existing users who expected segmentation outputs to appear only in `--brainweb-dir` will need a documented migration path.
- Public Python API impact: no required signature change for `get_mri`; behavior changes so `brainweb_dir` is honored in v2 segmentation/generated-contrast paths. Optional helper/API additions may be introduced if needed to support final-output saving cleanly.
- Tests: add focused CLI tests for output/cache separation and Python API tests for v2 `brainweb_dir` propagation without network downloads.
- Dependencies: no new runtime dependencies.
