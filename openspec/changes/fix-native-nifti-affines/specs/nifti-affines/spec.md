## ADDED Requirements

### Requirement: Native BrainWeb v1 NIfTI affines
The system SHALL save BrainWeb v1 native NIfTI outputs with a 1.0 mm isotropic, axis-aligned affine centered on the native array shape.

#### Scenario: Saving BrainWeb v1 contrast data
- **WHEN** a BrainWeb v1 contrast file is downloaded and saved as NIfTI
- **THEN** the saved affine SHALL use 1.0 mm voxel spacing on each spatial axis
- **AND** the affine translation SHALL be `(-90.5, -108.5, -90.5)` for native shape `(181, 217, 181)`

#### Scenario: Saving BrainWeb v1 segmentation data
- **WHEN** a BrainWeb v1 crisp or fuzzy segmentation file is downloaded and saved as NIfTI
- **THEN** the saved affine SHALL use 1.0 mm voxel spacing on each spatial axis
- **AND** the affine translation SHALL be `(-90.5, -108.5, -90.5)` for native shape `(181, 217, 181)`

### Requirement: Native BrainWeb v2 T1 NIfTI affine
The system SHALL save BrainWeb v2 native T1 NIfTI outputs with a 1.0 mm isotropic, axis-aligned affine centered on the native T1 array shape.

#### Scenario: Saving BrainWeb v2 T1 data
- **WHEN** a BrainWeb v2 T1 file is downloaded and saved as NIfTI
- **THEN** the saved affine SHALL use 1.0 mm voxel spacing on each spatial axis
- **AND** the affine translation SHALL be derived from native shape `(181, 256, 256)` as `(-90.5, -128.0, -128.0)`

### Requirement: Native BrainWeb v2 segmentation NIfTI affines
The system SHALL save BrainWeb v2 native segmentation NIfTI outputs with a 0.5 mm isotropic, axis-aligned affine centered on the native segmentation array shape.

#### Scenario: Saving BrainWeb v2 crisp segmentation data
- **WHEN** a BrainWeb v2 crisp segmentation file is downloaded and saved as NIfTI
- **THEN** the saved affine SHALL use 0.5 mm voxel spacing on each spatial axis
- **AND** the affine translation SHALL be `(-90.5, -108.5, -90.5)` for native shape `(362, 434, 362)`

#### Scenario: Saving BrainWeb v2 fuzzy segmentation data
- **WHEN** a BrainWeb v2 fuzzy segmentation file is downloaded and saved as NIfTI
- **THEN** the saved affine SHALL use 0.5 mm voxel spacing on each spatial axis
- **AND** the affine translation SHALL be `(-90.5, -108.5, -90.5)` for native shape `(362, 434, 362)`

### Requirement: Generated contrast affine propagation
The system SHALL return generated contrast data with the affine of the native segmentation file from which the contrast was derived.

#### Scenario: Returning a generated BrainWeb v2 contrast
- **WHEN** a BrainWeb v2 generated contrast is requested with `with_affine=True`
- **THEN** the returned affine SHALL match the BrainWeb v2 fuzzy segmentation affine
- **AND** the returned data SHALL remain on the segmentation grid

### Requirement: Affine-less output behavior
The system SHALL keep `.npy` output behavior unchanged because NumPy array files do not carry NIfTI affine metadata.

#### Scenario: Loading a NumPy array output
- **WHEN** a saved `.npy` BrainWeb output is loaded through the package
- **THEN** the loader SHALL continue returning the existing identity affine placeholder
