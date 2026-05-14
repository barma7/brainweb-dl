## Purpose
Define how Python APIs honor caller-provided BrainWeb cache/download directories for v2 native products and generated contrasts.

## Requirements

### Requirement: Python API honors brainweb_dir for v2 native products
The Python API SHALL use the caller-provided `brainweb_dir` for all BrainWeb v2 native product cache reads and writes.

#### Scenario: Requesting v2 T1 with brainweb_dir
- **WHEN** a caller requests `get_mri(<v2-subject>, "T1", brainweb_dir=<dir>)`
- **THEN** the native T1 cache file SHALL be read from or written under `<dir>`

#### Scenario: Requesting v2 crisp segmentation with brainweb_dir
- **WHEN** a caller requests `get_mri(<v2-subject>, "crisp", brainweb_dir=<dir>)`
- **THEN** the native crisp segmentation cache file SHALL be read from or written under `<dir>`

#### Scenario: Requesting v2 fuzzy segmentation with brainweb_dir
- **WHEN** a caller requests `get_mri(<v2-subject>, "fuzzy", brainweb_dir=<dir>)`
- **THEN** the native fuzzy segmentation cache file SHALL be read from or written under `<dir>`

### Requirement: Python API honors brainweb_dir for v2 generated contrasts
The Python API SHALL use the caller-provided `brainweb_dir` when loading the v2 fuzzy segmentation used to generate non-native contrasts.

#### Scenario: Requesting a generated v2 contrast with brainweb_dir
- **WHEN** a caller requests a generated v2 contrast such as `T2*` with `brainweb_dir=<dir>`
- **THEN** the fuzzy segmentation used to generate the contrast SHALL be read from or written under `<dir>`
- **AND** the generated contrast SHALL NOT silently use the default BrainWeb cache directory

### Requirement: Python API default cache behavior remains available
The Python API SHALL continue using the existing default BrainWeb cache resolution when no `brainweb_dir` is provided.

#### Scenario: Requesting data without brainweb_dir
- **WHEN** a caller requests data without `brainweb_dir`
- **THEN** the package SHALL continue resolving the native cache directory from `BRAINWEB_DIR` or the default user cache path
