## 1. API Structures and Loading

- [x] 1.1 Add `src/brainweb_dl/synthesize_contrast.py` with structured map, sequence, noise, and result dataclasses.
- [x] 1.2 Implement path-or-array loading for required quantitative maps using existing package array-loading helpers.
- [x] 1.3 Validate required map shapes and path-derived affines, and choose the first required map affine as the output affine.
- [x] 1.4 Export the public synthesis API from `src/brainweb_dl/__init__.py`.

## 2. Analytical Signal Models

- [x] 2.1 Implement required-map selection for SPGR/FLASH T1w, spin-echo T1w/T2w, and GRE T2*w models.
- [x] 2.2 Implement spin-echo clean signal synthesis with TR and TE in seconds.
- [x] 2.3 Implement SPGR/FLASH clean signal synthesis with flip angle in degrees and optional T2* echo decay.
- [x] 2.4 Implement GRE T2*w clean signal synthesis.
- [x] 2.5 Add metadata describing contrast, sequence parameters, units, required maps, and analytical model.

## 3. White-Matter SNR and Rician Noise

- [x] 3.1 Implement fuzzy segmentation path-or-array loading for noise calibration.
- [x] 3.2 Resolve the BrainWeb20 `white_matter` fuzzy channel and build the SNR mask from the configured fraction threshold.
- [x] 3.3 Compute `sigma = mean(clean_signal[wm_mask]) / snr` and fail clearly when the mask is unusable.
- [x] 3.4 Implement Rician magnitude noise from independent real and imaginary Gaussian samples.
- [x] 3.5 Make noisy synthesis reproducible with an RNG seed and store SNR/noise metadata.

## 4. Persistence and CLI

- [x] 4.1 Add synthesized contrast saving as NIfTI plus JSON sidecar metadata.
- [x] 4.2 Add a CLI entry point or command path that accepts map paths, sequence parameters, optional SNR/fuzzy inputs, and output path.
- [x] 4.3 Keep the CLI focused on path-based synthesis and ensure noisy CLI synthesis requires a fuzzy segmentation path.
- [x] 4.4 Update package entry points if a new console script is introduced.

## 5. Documentation

- [x] 5.1 Update README or user-facing docs with Python examples for array and path inputs.
- [x] 5.2 Document expected units, analytical signal equations, required maps by model, and unsupported physics.
- [x] 5.3 Document the SNR definition and Rician magnitude noise behavior.

## 6. Verification

- [x] 6.1 Add focused tests for required-map validation, path/array loading, shape and affine mismatch handling.
- [x] 6.2 Add focused tests for spin-echo, SPGR/FLASH, and GRE analytical formulas with small arrays.
- [x] 6.3 Add focused tests for white-matter SNR calibration, unusable mask errors, Rician noise, and RNG reproducibility.
- [x] 6.4 Add focused tests for persistence metadata and CLI path-based synthesis behavior.
- [x] 6.5 Run the repository health check with `C:\Users\marco\.conda\envs\pymarss\python.exe -m unittest discover -s tests -v`.
- [x] 6.6 Run `openspec validate add-analytical-contrast-synthesis --strict`.
