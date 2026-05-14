## Why

Generated contrasts currently derive voxel values by linearly mixing tissue
relaxation times from flat CSV tissue maps. This is not a quantitative MRI
parameter-map model, and it loses important semantics such as proton density,
field strength, units, and per-channel metadata.

BrainWeb20 fuzzy segmentations already provide tissue probability channels.
The package should use those channels, together with a structured JSON tissue
property model, to build quantitative maps and associated volume-fraction and
proton-density maps.

## What Changes

- Add a strict JSON tissue-property data model for BrainWeb20 channel metadata,
  BrainWeb download aliases, proton density, field-aware relaxation properties,
  field-independent ADC/chi values, units, and provisional-value markers.
- Make JSON the source of truth for BrainWeb20 fuzzy channel download aliases
  and quantitative-map generation. Existing CSV files remain packaged only as
  deprecated historical data.
- Add a separate quantitative-map API that accepts a downloaded fuzzy
  segmentation and returns a metadata-bearing result dataclass.
- Generate quantitative maps from fuzzy channels by dividing each 12-bit channel
  by 4095. The system does not per-voxel renormalize tissue fractions.
- Use deterministic proton-density-weighted apparent rate estimates for T1,
  T2, and T2* by default, with optional stochastic per-voxel sampling from
  JSON mean/std values.
- Add a `brainweb-dl-qmap` CLI for generating quantitative maps after fuzzy
  segmentation download.
- Save maps as NIfTI plus JSON sidecar metadata, or as HDF5 when requested.

## Non-Goals

- Do not implement a full MRI sequence simulator or acquisition fitting engine.
- Do not introduce canonical tissue grouping. BrainWeb20 maps are channel-based.
- Do not implement BrainWeb1 quantitative-map migration in this change.
- Do not support legacy linear relaxation-time mixing.
- Do not define authoritative conductivity, permittivity, or other properties
  beyond those present in the shipped JSON model.

## Capabilities

### New Capabilities

- `field-aware-tissue-properties`: Defines structured BrainWeb20 tissue-channel
  properties, JSON-backed fuzzy channel metadata, and quantitative-map
  generation from fuzzy BrainWeb segmentations.

### Modified Capabilities

- BrainWeb20 fuzzy download assembly uses JSON channel aliases instead of CSV
  rows.

## Impact

- Affected code: `src/brainweb_dl/_brainweb.py` BrainWeb20 fuzzy channel
  assembly; new quantitative-map implementation; package data under
  `src/brainweb_dl/data/`; CLI entry points.
- Affected public behavior: generated BrainWeb20 `T2`/`T2*`-style maps move out
  of `get_mri()` and into the new quantitative-map API/CLI. Legacy linear
  mixing is not preserved.
- Affected API: add a `get_quantitative_map()` API returning a dataclass with
  data, affine, units, and metadata.
- Affected CLI: add `brainweb-dl-qmap`.
- Dependencies: add `h5py` for HDF5 output support.
