## Context

The current generated-contrast implementation loads a CSV tissue map, reads columns such as `T2 (ms)`, and adds `fuzzy_fraction * sampled_tissue_value` into the output voxel. This produces a linear mixture of relaxation times, not a tissue-density-weighted apparent MRI relaxation estimate.

BrainWeb20 also does not include PD/density in the current CSV file, so tissue fractions are not weighted by available proton density before apparent relaxation values are estimated. A JSON structure similar to the OpenPhantom BrainWeb metadata can represent field strengths, canonical tissue names, download aliases, density, and multiple properties in one extensible format.

## Proposed Data Model

Add a JSON tissue-property file for BrainWeb20 with:

- dataset metadata and supported subject IDs
- supported field strengths, keyed as strings such as `"3"` and `"7"`
- canonical tissue names used by the public model
- BrainWeb download aliases for each canonical tissue
- density or PD-like relative weights per canonical tissue
- field-specific tissue properties such as `T1`, `T2`, `T2s`, `ADC`, or `chi`
- explicit units, preferably seconds for relaxation times and relative units for density

The loader should normalize this file into an internal structure with canonical tissue order, labels or aliases, density weights, and property arrays for the requested field strength.

## Apparent Relaxation Strategy

Generated apparent maps should mix tissue signal contributions instead of relaxation times. For a voxel and a property such as T2:

```text
w_t = fuzzy_fraction_t * density_t
S(TE) = sum_t w_t * exp(-TE / T2_t)
```

For a fast default apparent T2 estimate, use the initial log-slope at `TE = 0`:

```text
R2_app = sum_t w_t * (1 / T2_t) / sum_t w_t
T2_app = 1 / R2_app
```

For acquisition-aware behavior, support a two-point log-slope approximation:

```text
T2_app = -(TE2 - TE1) / log(S(TE2) / S(TE1))
```

The implementation should guard against zero-density or background-only voxels and return zero or a documented fill value in those locations.

## Compatibility

Keep the existing `get_mri(sub_id=4, contrast="T1")` behavior as a native BrainWeb T1 image load. The new behavior applies to generated contrasts derived from fuzzy segmentations, such as BrainWeb20 `T2` and `T2*`.

The CSV tissue maps may remain for backward compatibility during migration, but generated BrainWeb20 contrasts should prefer the structured JSON model once available.

## Open Questions

- Which field strength should be the default for generated BrainWeb20 maps?
- Should `T2*` be represented directly from `T2s`, or derived from `T2` and `T2'` when both are available?
- Should the public API expose `method="initial-slope"` and `method="two-point"` directly, or keep this internal until the behavior stabilizes?
