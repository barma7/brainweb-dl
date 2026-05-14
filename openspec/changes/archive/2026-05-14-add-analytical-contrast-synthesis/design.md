## Context

The package currently separates native BrainWeb MRI access in `mri.py` from
BrainWeb20 quantitative-map generation in `qmap.py`. Quantitative maps expose
PD, T1, T2, and T2* values with explicit units, but callers still need their
own code to turn those maps into weighted images for simple numerical phantom
experiments.

This change adds a new analytical contrast synthesis layer after quantitative
map generation:

```text
BrainWeb fuzzy segmentation
        -> qmap.py: PD, T1, T2, T2s maps
        -> synthesize_contrast.py: analytical weighted magnitude image
        -> optional NIfTI output and JSON sidecar metadata
```

The new module is intentionally separate from `mri.py` so `get_mri()` remains
focused on native BrainWeb products and segmentations. It is also separate from
`qmap.py` so quantitative-map generation remains independent from sequence
contrast choices.

## Goals / Non-Goals

**Goals:**

- Provide a structured Python API for synthesizing T1w, T2w, and T2*w images
  from quantitative maps.
- Accept quantitative maps and fuzzy segmentation inputs as either paths or
  pre-loaded arrays.
- Define the public units contract: relaxation maps in seconds, TR/TE in
  seconds, and flip angle in degrees.
- Validate only the maps needed by the selected sequence model.
- Add WM-calibrated Rician magnitude noise with reproducible RNG behavior.
- Preserve CLI/API parity so scripted workflows can pass qmap output paths.

**Non-Goals:**

- No Bloch simulation, k-space simulation, reconstruction, fitting, or
  sequence optimization.
- No coil sensitivity, correlated noise, multi-coil noncentral-chi magnitude
  model, B0/B1, off-resonance, diffusion, or susceptibility modeling.
- No changes to `get_mri()` behavior or the quantitative-map contract.
- No Numba parity requirement. This is a small NumPy-only analytical layer, not
  a simulator backend with Python/Numba implementations.

## Decisions

### Separate module and structured API

Add `synthesize_contrast.py` with structured objects for maps, sequence
parameters, noise configuration, and synthesis results. A structured API makes
required-map validation and future CLI wiring clearer than a loose collection
of positional arrays.

Alternative considered: add synthesis to `qmap.py`. That would couple
quantitative-map construction to sequence signal equations and make qmap
responsible for two different layers of the model.

### Path-or-array inputs

Map fields accept either pre-loaded arrays or paths supported by existing
`load_array()` behavior. Path inputs provide data and affine metadata for CLI
and file-based workflows; array inputs keep the Python API convenient for
notebook and testing use. When multiple required map paths provide affines, the
implementation compares them and uses the first required map affine as the
output affine.

Alternative considered: require NIfTI objects or paths only. That would be
heavier for Python users and less consistent with the existing qmap API, which
already accepts paths or arrays for fuzzy segmentation input.

### Explicit units and signal equations

The public API uses seconds for `TR` and `TE`, degrees for `flip_angle`, and
seconds for relaxation maps. This matches qmap relaxation outputs and avoids
hidden millisecond conversion at the API boundary.

First-version signal equations:

```text
Spin echo:
S = PD * (1 - exp(-TR / T1)) * exp(-TE / T2)

SPGR/FLASH:
E1 = exp(-TR / T1)
S = PD * sin(alpha) * (1 - E1) / (1 - cos(alpha) * E1)
S *= exp(-TE / T2s) when TE > 0

GRE T2*w:
S = PD * exp(-TE / T2s)
```

The synthesis result is a clean magnitude signal before optional noise. Inputs
with non-positive relaxation values do not contribute where division or
exponential decay would be undefined; affected voxels are set to zero.

### Required-map validation by model

The implementation validates only maps needed by the selected model. SPGR T1w
requires PD and T1, and requires T2s when TE is positive. Spin-echo T1w/T2w
requires PD, T1, and T2 because both TR recovery and TE decay are part of the
declared equation. GRE T2*w requires PD and T2s.

Alternative considered: require PD, T1, T2, and T2s for every synthesis call.
That would simplify validation but would make legitimate workflows provide
unused maps.

### White-matter SNR calibration and Rician magnitude noise

Noise calibration uses BrainWeb fuzzy white-matter voxels rather than
background or whole-image statistics:

```text
wm_mask = fuzzy[..., white_matter_channel] >= threshold
sigma = mean(clean_signal[wm_mask]) / snr
```

The white-matter channel name is `white_matter` in the BrainWeb20 tissue
metadata. The default threshold is high enough to select mostly pure white
matter. If no voxels pass the threshold, the call fails rather than silently
falling back to background or image percentiles.

For magnitude output, noise is modeled as Rician:

```text
real = clean_signal + N(0, sigma)
imag = N(0, sigma)
noisy = sqrt(real**2 + imag**2)
```

The requested SNR is defined against the clean underlying magnitude mean in the
white-matter mask divided by sigma. It is not defined as the mean of the final
Rician-biased magnitude image divided by its measured standard deviation.

## Risks / Trade-offs

- [Risk] Analytical equations can be mistaken for scanner-realistic
  simulation. -> Mitigation: document the first-version physics scope and
  unsupported effects in API docs, CLI help, and metadata.
- [Risk] Path-or-array inputs create shape and affine edge cases. -> Mitigation:
  validate spatial shape equality for required inputs and compare affines from
  required path inputs before synthesis.
- [Risk] Rician noise surprises users expecting additive Gaussian image noise.
  -> Mitigation: make magnitude/Rician behavior explicit and store noise model,
  SNR definition, tissue, and threshold in result metadata.
- [Risk] White-matter SNR calibration depends on fuzzy channel ordering. ->
  Mitigation: resolve the channel by tissue metadata name, not by a hard-coded
  index where possible, and fail clearly if the channel is absent.
- [Risk] CLI scope could grow too broad. -> Mitigation: keep the CLI focused on
  consuming existing qmap/fuzzy paths and saving one synthesized result.
