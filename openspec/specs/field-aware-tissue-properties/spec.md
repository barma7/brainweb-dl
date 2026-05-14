# field-aware-tissue-properties Specification

## Purpose
TBD - created by archiving change add-field-aware-tissue-properties. Update Purpose after archive.
## Requirements
### Requirement: BrainWeb20 JSON tissue-channel metadata
The system SHALL support a strict JSON metadata file for BrainWeb20 tissue
channels.

#### Scenario: Loading BrainWeb20 tissue-channel metadata
- **WHEN** BrainWeb20 fuzzy download or quantitative-map logic needs tissue metadata
- **THEN** the system SHALL load channel names, labels, BrainWeb download aliases, proton density, field strength units, property units, field-specific relaxation properties, ADC, chi, and provisional markers from package JSON data
- **AND** the metadata SHALL declare units explicitly
- **AND** the metadata SHALL be channel-based rather than canonical-tissue-based

### Requirement: JSON-backed BrainWeb20 fuzzy channel assembly
BrainWeb20 fuzzy segmentation downloads SHALL use JSON channel aliases as the
source of truth.

#### Scenario: Downloading BrainWeb20 fuzzy segmentation
- **WHEN** the system assembles a BrainWeb20 fuzzy segmentation
- **THEN** each 4D channel SHALL correspond to the ordered channel entries in the JSON metadata
- **AND** existing CSV files SHALL NOT be required for BrainWeb20 fuzzy channel assembly

### Requirement: Quantitative-map API result
The system SHALL expose a quantitative-map API that is separate from BrainWeb
download APIs.

#### Scenario: Creating a quantitative map from fuzzy segmentation
- **WHEN** a caller provides a BrainWeb20 fuzzy segmentation path or array and requests a quantitative property
- **THEN** the system SHALL return a result dataclass containing the map data, affine, property name, units, field strength, source channel names, and metadata

### Requirement: Fuzzy channel fraction conversion
The system SHALL convert BrainWeb fuzzy channels to volume fractions without
per-voxel renormalization.

#### Scenario: Converting raw BrainWeb fuzzy channels
- **WHEN** the input fuzzy segmentation contains 12-bit integer channel values
- **THEN** each channel SHALL be divided by 4095 independently
- **AND** the system SHALL NOT renormalize the resulting fractions to sum to one per voxel

### Requirement: Volume-fraction and proton-density outputs
The system SHALL generate tissue volume-fraction and proton-density contribution
maps.

#### Scenario: Generating per-tissue volume fractions
- **WHEN** the caller requests `VF`
- **THEN** the result data SHALL be a 4D array with one channel per present BrainWeb tissue channel

#### Scenario: Generating total volume fraction
- **WHEN** the caller requests `VF_TOTAL`
- **THEN** the result data SHALL be a 3D sum of present tissue volume fractions

#### Scenario: Generating proton-density contribution maps
- **WHEN** the caller requests `PD`
- **THEN** the result data SHALL be a 4D array where each tissue channel equals `fraction_t * PD_t`

#### Scenario: Generating total proton density
- **WHEN** the caller requests `PD_TOTAL`
- **THEN** the result data SHALL be a 3D sum of per-tissue proton-density contributions

### Requirement: Apparent relaxation maps
The system SHALL generate apparent T1, T2, and T2* maps using proton-density
weighted apparent-rate estimates.

#### Scenario: Generating deterministic apparent relaxation maps
- **WHEN** a caller requests `T1`, `T2`, or `T2s`
- **THEN** the system SHALL compute tissue weights as `fraction_t * PD_t`
- **AND** the apparent relaxation rate SHALL be the weighted mean of tissue relaxation rates
- **AND** the apparent relaxation time SHALL be the reciprocal of that apparent rate
- **AND** output relaxation values SHALL be in seconds
- **AND** non-positive relaxation times SHALL NOT contribute to the estimate

#### Scenario: Generating stochastic apparent relaxation maps
- **WHEN** stochastic generation is enabled with an RNG seed
- **THEN** the system SHALL sample per-voxel tissue relaxation values from JSON mean/std values reproducibly
- **AND** sampled relaxation times SHALL be clipped to positive values before rate estimation

### Requirement: ADC and susceptibility maps
The system SHALL generate ADC and susceptibility maps from JSON channel
properties.

#### Scenario: Generating ADC maps
- **WHEN** the caller requests `ADC`
- **THEN** the system SHALL compute `ADC_app = sum(fraction_t * PD_t * ADC_t) / sum(fraction_t * PD_t)`

#### Scenario: Generating susceptibility maps
- **WHEN** the caller requests `chi`
- **THEN** the system SHALL compute a volume-fraction-weighted susceptibility sum
- **AND** background susceptibility SHALL use the JSON air value in ppm

### Requirement: Quantitative-map persistence
The system SHALL save quantitative-map outputs with metadata.

#### Scenario: Saving as NIfTI
- **WHEN** a caller saves a quantitative-map result to `.nii` or `.nii.gz`
- **THEN** the system SHALL write the image as NIfTI
- **AND** the system SHALL write a JSON sidecar containing field strength, output units, source units, method, source channels, and source property metadata

#### Scenario: Saving as HDF5
- **WHEN** a caller saves one or more quantitative-map results to `.h5` or `.hdf5`
- **THEN** the system SHALL store arrays and metadata in the HDF5 file

### Requirement: Quantitative-map CLI
The system SHALL provide a dedicated CLI for BrainWeb20 quantitative maps.

#### Scenario: Generating a single quantitative map from the CLI
- **WHEN** a user runs `brainweb-dl-qmap <subject> --property T2 --field-strength 3 --output <path>`
- **THEN** the CLI SHALL download or load the subject's BrainWeb20 fuzzy segmentation
- **AND** the CLI SHALL generate the requested quantitative map
- **AND** the CLI SHALL save the result using the requested output format

#### Scenario: Generating all quantitative maps from the CLI
- **WHEN** a user runs `brainweb-dl-qmap <subject> --property all --output <path>`
- **THEN** the CLI SHALL generate all supported quantitative maps

