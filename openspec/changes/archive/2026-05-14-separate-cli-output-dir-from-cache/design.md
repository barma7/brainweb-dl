## Context

The current CLI uses `--brainweb-dir` as the directory passed into native BrainWeb download helpers. For crisp/fuzzy segmentation commands, that helper path is also the only saved output. For T1/T2/T2* commands, the CLI loads data through `get_mri()` and then writes a second final NIfTI file into the current working directory. This makes `--brainweb-dir` appear to mean "output directory" for segmentations but "cache directory" for contrasts.

The Python API has a related consistency issue: the v2 T1 path passes `brainweb_dir`, but v2 segmentation and generated-contrast paths currently do not pass `brainweb_dir` into `get_brainweb20()`. Generated contrasts then apply tissue maps to a fuzzy segmentation that may come from the default cache instead of the caller-provided directory.

## Goals / Non-Goals

**Goals:**
- Make the CLI final output destination explicit and consistent for all supported products.
- Preserve `--brainweb-dir` as the native BrainWeb cache/download directory.
- Add a CLI output option that defaults predictably and avoids writing unexpected files outside the selected output destination.
- Ensure `get_mri(..., brainweb_dir=...)` honors the provided directory for v2 T1, v2 crisp/fuzzy segmentations, and v2 generated contrasts.
- Preserve existing download/cache behavior unless callers opt into a different final output location.
- Cover behavior with focused tests that avoid network downloads.

**Non-Goals:**
- Add a no-cache or in-memory-only mode.
- Change native BrainWeb cache filenames.
- Change image arrays, tissue maps, generated contrast physics, affine metadata, or resampling behavior.
- Introduce Python/Numba simulator parity work; this package change does not touch a simulator backend.

## Decisions

### Add an explicit CLI output directory

Introduce `--output-dir` as the directory where the CLI writes the final requested product. `--brainweb-dir` remains the cache/download directory. If `--output-dir` is omitted, the CLI should keep the current working directory as the default final output location for backward compatibility with existing contrast commands.

Alternative considered: reinterpret `--brainweb-dir` as the final output directory. That would match current segmentation behavior but would make the option name and README cache semantics misleading, and it would remove a way to choose cache location independently from final export location.

### Use one CLI output path strategy for all product types

All CLI branches should resolve a final output path under `--output-dir`, write exactly that requested output, and print that path. Native cache files may still be created under `--brainweb-dir`, but they are internal cache artifacts rather than the reported final output.

For contrast products, the CLI can continue using `get_mri(..., with_affine=True)` and save the returned array/affine to the final output path. For segmentation products, the CLI should also produce a final output path through the same export path instead of returning the cache helper path directly.

Alternative considered: add `--output-dir` only for contrast commands. That leaves the current inconsistency in place.

### Keep Python API cache semantics explicit

The Python API should consistently treat `brainweb_dir` as the native BrainWeb cache/download directory. `get_mri()` should pass `brainweb_dir` through every internal v2 path, including:

- v2 T1 through `get_brainweb20_T1()`
- v2 crisp/fuzzy through `get_brainweb20()`
- v2 generated contrasts through `get_brainweb20(..., segmentation=Segmentation.FUZZY)`

Alternative considered: add a separate Python API output directory now. That is unnecessary for `get_mri()`, which returns arrays by default; final-output saving is primarily a CLI concern.

### Defer no-cache support

The current implementation downloads into memory using `io.BytesIO` before decoding, but still saves native cache files. A no-cache mode would require changing helper contracts, fuzzy segmentation assembly, and cache hit behavior. It should be a separate change after output routing is clear.

## Risks / Trade-offs

- Users who currently rely on segmentation commands writing only to `--brainweb-dir` will see a behavior change when they use `--output-dir`. Mitigation: document that `--brainweb-dir` is cache and `--output-dir` is final output.
- Keeping current working directory as the default output directory preserves contrast behavior but means segmentation commands without `--output-dir` may gain a current-directory final output in addition to cache files. Mitigation: tests and help text should make this explicit.
- Final output for segmentations may duplicate native cache files when `--output-dir` differs from `--brainweb-dir`. Mitigation: duplication is the intended result of separating cache from exported output; no-cache can be considered later.
- Passing `brainweb_dir` consistently may change which cached fuzzy segmentation is used for generated v2 contrasts. Mitigation: this is a bug fix that aligns behavior with caller intent.
