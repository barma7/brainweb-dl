## 1. Core Data Operations

- [x] 1.1 Add a nasal-air correction module with a correction result dataclass.
- [x] 1.2 Implement `patch_fuzzy_with_air_mask(...)` for integer and normalized floating-point fuzzy arrays.
- [x] 1.3 Implement geometry validation for fuzzy shape, mask shape, and path-based affine matching.
- [x] 1.4 Implement corrected fuzzy saving with JSON sidecar provenance.

## 2. T1w Intermediate Generation

- [x] 2.1 Implement T1w intermediate generation from source fuzzy using existing `get_quantitative_map()` and `synthesize_contrast()` APIs.
- [x] 2.2 Define documented default SPGR/FLASH T1w sequence parameters and expose overrides in the Python workflow.
- [x] 2.3 Ensure the synthesized T1w output preserves the fuzzy segmentation spatial shape and affine.

## 3. PARASIDE Subprocess Boundary

- [x] 3.1 Implement PARASIDE command construction for `conda run --no-capture-output -p <env> paraside --i <input> --m <model>`.
- [x] 3.2 Add an optional direct PARASIDE executable mode without importing PARASIDE.
- [x] 3.3 Implement subprocess execution with clear errors for non-zero exits.
- [x] 3.4 Implement expected PARASIDE output-path resolution and missing-output errors.

## 4. Public API and CLI

- [x] 4.1 Add `correct_fuzzy_nasal_air(...)` as the end-to-end Python workflow.
- [x] 4.2 Export the new public API and pure patching helper from `brainweb_dl.__init__`.
- [x] 4.3 Add a `brainweb-dl-nasal-air-correct` CLI entry point with subject, `--brainweb-dir`, `--output`, `--paraside-env`, `--paraside-executable`, `--paraside-model`, `--keep-intermediates`, and sequence override options.
- [x] 4.4 Ensure the CLI reports the corrected fuzzy output path and does not report native cache artifacts as the primary result.

## 5. Tests

- [x] 5.1 Add focused tests for integer fuzzy patching, normalized fuzzy patching, and collapsing nonzero PARASIDE labels.
- [x] 5.2 Add tests for shape and affine mismatch failures.
- [x] 5.3 Add tests for PARASIDE command construction, failed subprocess handling, and missing PARASIDE output handling without running PARASIDE.
- [x] 5.4 Add tests for Python workflow orchestration using monkeypatched T1w generation and PARASIDE execution.
- [x] 5.5 Add tests for CLI argument parsing and output/provenance behavior.

## 6. Documentation and Verification

- [x] 6.1 Update README usage notes for the nasal-air correction workflow and clarify that PARASIDE is an optional external dependency.
- [x] 6.2 Document the nonzero mask rule, derivative output behavior, and use of corrected fuzzy paths for subsequent qmap generation.
- [x] 6.3 Run `openspec validate correct-fuzzy-nasal-air-with-paraside --strict`.
- [x] 6.4 Run the repository health check with `C:\Users\marco\.conda\envs\pymarss\python.exe -m unittest discover -s tests -v`.
- [x] 6.5 No Python/Numba agreement check is required because this change does not modify simulator backend behavior.
