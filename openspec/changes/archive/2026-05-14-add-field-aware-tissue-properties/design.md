## Context

The current generated-contrast implementation loads CSV rows, reads columns such
as `T2 (ms)`, and computes a linear mixture of relaxation times. That output is
not a density-aware apparent quantitative map. BrainWeb20 also lacks proton
density in the current CSV file, so tissue fractions are not weighted by proton
density before apparent relaxation estimates are computed.

The new model separates downloading from quantitative-map construction:

```text
BrainWeb20 fuzzy download -> 4D NIfTI with raw 12-bit channels
                         -> quantitative-map API/CLI
                         -> NIfTI+JSON or HDF5 outputs
```

## Data Model

Add a strict JSON package-data file for BrainWeb20 with channel-based entries:

- dataset metadata and supported channel count
- unit declarations for all properties
- BrainWeb download alias per channel
- BrainWeb label per channel
- proton density in `[0, 1]`, where `1` means 100%
- field-independent `ADC` and `chi`
- field-specific `T1`, `T2`, and `T2s` mean/std values in milliseconds
- optional provisional-value markers

Field strength keys are numeric strings such as `"3.0"`; the field-strength
unit is declared separately as tesla. The Python default field strength is
`3.0`.

The model does not define canonical tissues. If two BrainWeb channels should
behave similarly, the JSON assigns them the same property values.

## Volume Fractions

BrainWeb fuzzy data are downloaded as 12-bit integer probability channels. Each
channel is converted independently:

```text
fraction_t = raw_channel_t / 4095
```

The system SHALL NOT renormalize fractions per voxel. This avoids artificially
inflating present tissue channels when other channels are missing or when the
segmentation total is below one.

Unexpected extra channels are an error. Known JSON channels absent from an input
segmentation are logged and omitted from the map computation.

## Quantitative Maps

The quantitative-map API returns a result dataclass containing data, affine,
property name, units, field strength, source channels, and metadata.

Outputs:

- `VF`: 4D tissue volume-fraction array, one channel per present BrainWeb tissue.
- `VF_TOTAL`: 3D sum of tissue volume fractions.
- `PD`: 4D per-tissue proton-density contribution, `fraction_t * PD_t`.
- `PD_TOTAL`: 3D total proton-density contribution.
- `T1`, `T2`, `T2s`: 3D apparent relaxation maps in seconds.
- `ADC`: 3D proton-density-weighted ADC map.
- `chi`: 3D volume-fraction-weighted susceptibility map in ppm.

For relaxation maps, use a deterministic apparent-rate estimate by default:

```text
w_t = fraction_t * PD_t
R_app = sum_t(w_t / T_t) / sum_t(w_t)
T_app = 1 / R_app
```

`T_t` is loaded from JSON in milliseconds and converted to seconds for output.
Channels with non-positive relaxation times do not contribute. Background does
not bias relaxation or ADC estimates, but it participates in volume fraction,
proton-density, and susceptibility outputs according to its JSON values.

For ADC:

```text
ADC_app = sum_t(w_t * ADC_t) / sum_t(w_t)
```

For susceptibility:

```text
chi_app = sum_t(fraction_t * chi_t)
```

The background air susceptibility value is represented in JSON as `0.36 ppm`.

## Stochastic Numerical Phantoms

Default quantitative maps are deterministic. When stochastic generation is
enabled, the implementation samples relaxation values independently per voxel
and channel from JSON mean/std values, uses the provided RNG seed for
reproducibility, and clips sampled relaxation times to positive values.

## Persistence

NIfTI output stores image arrays and writes a sidecar JSON metadata file. HDF5
output stores arrays and metadata in a single file. Metadata includes source
property file identity, output units, source units, field strength, method,
channel names, and whether stochastic sampling was enabled.

## Compatibility

The existing CSV files remain in package data as deprecated historical files.
BrainWeb20 fuzzy download assembly and quantitative-map generation use JSON as
the source of truth. Legacy linear relaxation-time mixing is not supported.

BrainWeb1 quantitative-map migration is intentionally deferred.
