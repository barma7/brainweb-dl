## 1. Python API Cache Consistency

- [x] 1.1 Update v2 `get_mri()` segmentation path so `brainweb_dir` is passed to `get_brainweb20()`.
- [x] 1.2 Update v2 generated-contrast path so the fuzzy segmentation is read from or written under the caller-provided `brainweb_dir`.
- [x] 1.3 Add focused Python API tests proving v2 crisp/fuzzy/generated contrast paths pass the requested `brainweb_dir` without requiring network downloads.

## 2. CLI Output Routing

- [x] 2.1 Add a `--output-dir` CLI option and resolve it to the final output directory, defaulting to the current working directory when omitted.
- [x] 2.2 Refactor CLI contrast handling so final outputs are written under `--output-dir` while native cache artifacts remain under `--brainweb-dir`.
- [x] 2.3 Refactor CLI crisp/fuzzy handling so final segmentation outputs are written under `--output-dir` using the same output routing as contrasts.
- [x] 2.4 Ensure CLI printed messages report final output paths, not native cache artifact paths.

## 3. Documentation

- [x] 3.1 Update CLI help text and README usage notes to distinguish `--brainweb-dir` as cache/download directory from `--output-dir` as final output directory.
- [x] 3.2 Document compatibility behavior for users who previously relied on segmentation outputs being saved directly in `--brainweb-dir`.

## 4. Verification

- [x] 4.1 Add focused CLI tests covering separate cache and output directories for at least one contrast and one segmentation.
- [x] 4.2 Run focused tests for Python API cache propagation and CLI output routing.
- [x] 4.3 Run the repository health check with `C:\Users\marco\.conda\envs\pymarss\python.exe -m unittest discover -s tests -v`.
- [x] 4.4 Run `openspec validate separate-cli-output-dir-from-cache --strict`.
