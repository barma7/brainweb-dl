## ADDED Requirements

### Requirement: Structured contrast synthesis API
The system SHALL expose a structured Python API for analytical MRI contrast
synthesis from quantitative maps.

#### Scenario: Synthesizing from pre-loaded arrays
- **WHEN** a caller provides pre-loaded NumPy arrays for the maps required by
  the selected contrast model
- **THEN** the system SHALL synthesize a 3D image array
- **AND** the system SHALL return a result containing image data, affine,
  contrast name, sequence metadata, required map names, units metadata, and
  noise metadata

#### Scenario: Synthesizing from map paths
- **WHEN** a caller provides paths for the maps required by the selected
  contrast model
- **THEN** the system SHALL load those maps using the package array-loading
  behavior
- **AND** the system SHALL use the first required map affine as the output
  affine
- **AND** the system SHALL reject required map inputs whose spatial shapes do
  not match
- **AND** the system SHALL reject required path inputs whose affines do not
  match within numerical tolerance

#### Scenario: Mixed path and array inputs
- **WHEN** a caller provides a mixture of path and array map inputs
- **THEN** the system SHALL load path inputs and use array inputs directly
- **AND** the system SHALL validate only the required inputs for the selected
  contrast model

### Requirement: Required map validation by contrast model
The system SHALL require only the quantitative maps used by the selected
analytical contrast model.

#### Scenario: SPGR FLASH T1-weighted synthesis
- **WHEN** a caller requests SPGR or FLASH T1-weighted synthesis with `TE` equal
  to zero
- **THEN** the system SHALL require `PD` and `T1` maps
- **AND** the system SHALL NOT require `T2` or `T2s` maps

#### Scenario: SPGR FLASH T1-weighted synthesis with echo decay
- **WHEN** a caller requests SPGR or FLASH T1-weighted synthesis with `TE`
  greater than zero
- **THEN** the system SHALL require `PD`, `T1`, and `T2s` maps
- **AND** the system SHALL NOT require a `T2` map

#### Scenario: Spin-echo synthesis
- **WHEN** a caller requests spin-echo T1-weighted or T2-weighted synthesis
- **THEN** the system SHALL require `PD`, `T1`, and `T2` maps
- **AND** the system SHALL NOT require a `T2s` map

#### Scenario: Gradient-echo T2-star weighted synthesis
- **WHEN** a caller requests gradient-echo T2-star weighted synthesis
- **THEN** the system SHALL require `PD` and `T2s` maps
- **AND** the system SHALL NOT require `T1` or `T2` maps unless the selected
  model explicitly includes TR and flip-angle saturation

### Requirement: Sequence units and analytical signal conventions
The system SHALL document and enforce sequence parameter units and analytical
signal conventions for contrast synthesis.

#### Scenario: Unit interpretation
- **WHEN** a caller provides sequence parameters
- **THEN** the system SHALL interpret `TR` and `TE` as seconds
- **AND** the system SHALL interpret `flip_angle` as degrees
- **AND** the system SHALL interpret relaxation maps `T1`, `T2`, and `T2s` as
  seconds
- **AND** the system SHALL treat `PD` as an arbitrary normalized
  proton-density-like signal scale

#### Scenario: Spin-echo signal model
- **WHEN** a caller requests spin-echo synthesis
- **THEN** the system SHALL compute clean signal as
  `PD * (1 - exp(-TR / T1)) * exp(-TE / T2)`

#### Scenario: SPGR FLASH signal model
- **WHEN** a caller requests SPGR or FLASH synthesis
- **THEN** the system SHALL compute `E1 = exp(-TR / T1)`
- **AND** the system SHALL compute clean signal as
  `PD * sin(alpha) * (1 - E1) / (1 - cos(alpha) * E1)`, where `alpha` is the
  flip angle converted to radians
- **AND** the system SHALL multiply by `exp(-TE / T2s)` when `TE` is greater
  than zero

#### Scenario: Gradient-echo T2-star signal model
- **WHEN** a caller requests gradient-echo T2-star weighted synthesis
- **THEN** the system SHALL compute clean signal as `PD * exp(-TE / T2s)`

### Requirement: White-matter SNR calibration
The system SHALL calibrate requested SNR from clean signal in BrainWeb fuzzy
white-matter voxels.

#### Scenario: Deriving noise sigma from white matter
- **WHEN** a caller requests noise with an SNR value and provides a BrainWeb
  fuzzy segmentation path or array
- **THEN** the system SHALL identify the fuzzy `white_matter` tissue channel
- **AND** the system SHALL form an SNR mask from voxels whose white-matter
  fraction is greater than or equal to the configured threshold
- **AND** the system SHALL compute `sigma = mean(clean_signal[mask]) / snr`

#### Scenario: Missing white matter mask
- **WHEN** noise is requested and the fuzzy segmentation does not contain a
  usable white-matter mask
- **THEN** the system SHALL raise an error
- **AND** the system SHALL NOT fall back to background, whole-image, or
  percentile-based SNR calibration

#### Scenario: SNR metadata
- **WHEN** the system returns or saves a noisy synthesized contrast
- **THEN** the result metadata SHALL include requested SNR, calibration tissue,
  tissue fraction threshold, clean calibration signal, sigma, and the SNR
  definition

### Requirement: Rician magnitude noise
The system SHALL model noisy magnitude images using Rician noise statistics.

#### Scenario: Adding magnitude noise
- **WHEN** a caller requests noise for a synthesized magnitude image
- **THEN** the system SHALL add independent zero-mean Gaussian noise with
  standard deviation `sigma` to real and imaginary channels
- **AND** the system SHALL return
  `sqrt((clean_signal + real_noise)^2 + imag_noise^2)`

#### Scenario: Reproducible noise
- **WHEN** a caller provides an RNG seed for noisy synthesis
- **THEN** repeated calls with the same inputs and seed SHALL produce identical
  noisy image data

#### Scenario: Clean synthesis
- **WHEN** a caller does not request noise
- **THEN** the system SHALL return the clean analytical magnitude signal

### Requirement: Synthesized contrast persistence and CLI
The system SHALL support saving synthesized contrast results and expose
CLI-compatible behavior for path-based workflows.

#### Scenario: Saving a synthesized contrast
- **WHEN** a caller saves a synthesized contrast result to `.nii` or `.nii.gz`
- **THEN** the system SHALL write the synthesized image as NIfTI
- **AND** the system SHALL write a JSON sidecar containing contrast, sequence
  parameters, units, required maps, analytical model, and noise metadata

#### Scenario: CLI synthesis from qmap paths
- **WHEN** a user runs the contrast synthesis CLI with map paths, sequence
  parameters, and an output path
- **THEN** the CLI SHALL synthesize the requested contrast from those maps
- **AND** the CLI SHALL save the image and sidecar metadata to the requested
  output path

#### Scenario: CLI noisy synthesis requires fuzzy segmentation
- **WHEN** a user runs the contrast synthesis CLI with `--snr`
- **THEN** the CLI SHALL require a BrainWeb fuzzy segmentation path for
  white-matter SNR calibration
