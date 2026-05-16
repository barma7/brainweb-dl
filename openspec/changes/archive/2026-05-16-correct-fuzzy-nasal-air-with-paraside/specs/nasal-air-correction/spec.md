## ADDED Requirements

### Requirement: Corrected BrainWeb20 fuzzy derivative
The system SHALL produce a corrected BrainWeb20 fuzzy segmentation derivative that preserves the raw BrainWeb fuzzy cache artifact by default.

#### Scenario: Saving corrected fuzzy output
- **WHEN** a user runs nasal-air correction for a BrainWeb20 subject and provides an output path
- **THEN** the system SHALL save the corrected fuzzy segmentation to the requested output path
- **AND** the system SHALL NOT overwrite the native BrainWeb fuzzy cache artifact by default
- **AND** the corrected fuzzy segmentation SHALL use the source fuzzy affine

#### Scenario: Writing correction provenance
- **WHEN** the system saves a corrected fuzzy segmentation
- **THEN** the system SHALL write a JSON sidecar next to the corrected segmentation
- **AND** the sidecar SHALL record the source fuzzy path, corrected output path, PARASIDE mask path, PARASIDE mask rule, patched voxel count, PARASIDE environment or executable configuration, PARASIDE model path, and T1w synthesis settings

### Requirement: T1-weighted PARASIDE input on fuzzy grid
The system SHALL synthesize the T1-weighted PARASIDE input on the same spatial grid as the BrainWeb20 fuzzy segmentation.

#### Scenario: Synthesizing T1w input
- **WHEN** the nasal-air correction workflow prepares PARASIDE input from a BrainWeb20 fuzzy segmentation
- **THEN** the system SHALL derive quantitative maps from that fuzzy segmentation
- **AND** the system SHALL synthesize a T1-weighted magnitude image using seconds for relaxation and sequence timing parameters
- **AND** the default synthesized T1-weighted image SHALL use SPGR/FLASH `TE=0.004 s`
- **AND** the default synthesized T1-weighted image SHALL include white-matter-calibrated Rician noise at `SNR=10`
- **AND** the synthesized T1-weighted image SHALL have the same spatial shape and affine as the source fuzzy segmentation

#### Scenario: Avoiding native BrainWeb20 T1w input
- **WHEN** the nasal-air correction workflow needs PARASIDE input for a BrainWeb20 subject
- **THEN** the system SHALL NOT use the native BrainWeb20 T1w download as the default PARASIDE input

### Requirement: External PARASIDE invocation
The system SHALL run PARASIDE as an external process using caller-provided PARASIDE environment or executable configuration.

#### Scenario: Running PARASIDE through a conda environment
- **WHEN** a caller provides a PARASIDE conda environment path and PARASIDE model path
- **THEN** the system SHALL invoke PARASIDE through that environment without importing PARASIDE into the current Python process
- **AND** the system SHALL pass the synthesized T1-weighted image path and model path to PARASIDE

#### Scenario: PARASIDE command failure
- **WHEN** the PARASIDE subprocess exits unsuccessfully
- **THEN** the system SHALL raise an error
- **AND** the system SHALL NOT save a corrected fuzzy segmentation as if correction succeeded

#### Scenario: Missing PARASIDE output
- **WHEN** the PARASIDE subprocess succeeds but the expected segmentation output is missing
- **THEN** the system SHALL raise an error
- **AND** the system SHALL report the expected PARASIDE output path

### Requirement: Nonzero-mask fuzzy patching
The system SHALL patch every nonzero PARASIDE segmentation voxel into the BrainWeb20 fuzzy background channel.

#### Scenario: Patching integer fuzzy channels
- **WHEN** an integer BrainWeb20 fuzzy segmentation and a PARASIDE label mask are patched
- **THEN** every voxel whose mask label is not zero SHALL have background channel value `4095`
- **AND** every non-background channel in those voxels SHALL have value `0`
- **AND** voxels whose mask label is zero SHALL remain unchanged

#### Scenario: Patching normalized fuzzy channels
- **WHEN** a normalized floating-point BrainWeb20 fuzzy segmentation and a PARASIDE label mask are patched
- **THEN** every voxel whose mask label is not zero SHALL have background channel value `1.0`
- **AND** every non-background channel in those voxels SHALL have value `0.0`
- **AND** voxels whose mask label is zero SHALL remain unchanged

#### Scenario: Collapsing PARASIDE labels
- **WHEN** a PARASIDE mask contains multiple nonzero label values
- **THEN** the system SHALL treat all nonzero labels as the same nasal-cavity mask

### Requirement: Geometry validation before correction
The system SHALL validate fuzzy and PARASIDE mask geometry before applying nasal-air correction.

#### Scenario: Shape mismatch
- **WHEN** the PARASIDE mask spatial shape does not match the fuzzy segmentation spatial shape
- **THEN** the system SHALL raise an error
- **AND** the system SHALL NOT write a corrected fuzzy segmentation

#### Scenario: Affine mismatch
- **WHEN** path-based fuzzy and PARASIDE mask inputs have affines that do not match within numerical tolerance
- **THEN** the system SHALL raise an error
- **AND** the system SHALL NOT silently resample the PARASIDE mask

### Requirement: Nasal-air correction API and CLI
The system SHALL expose nasal-air correction through Python API and CLI workflows.

#### Scenario: Python correction workflow
- **WHEN** a caller invokes the Python nasal-air correction API with a BrainWeb20 subject, BrainWeb directory, output path, PARASIDE environment or executable configuration, and PARASIDE model path
- **THEN** the system SHALL generate or load the required source fuzzy segmentation
- **AND** the system SHALL run the correction workflow
- **AND** the system SHALL return correction result metadata including the corrected fuzzy path and patched voxel count

#### Scenario: CLI correction workflow
- **WHEN** a user runs the nasal-air correction CLI with subject, output path, PARASIDE environment or executable configuration, and PARASIDE model path
- **THEN** the CLI SHALL run the correction workflow
- **AND** the CLI SHALL report the corrected fuzzy output path
