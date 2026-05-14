## ADDED Requirements

### Requirement: Explicit CLI final output directory
The CLI SHALL provide an explicit `--output-dir` option that controls where final requested output files are written.

#### Scenario: Writing a contrast output to an explicit output directory
- **WHEN** a user runs the CLI for a supported contrast with `--output-dir <dir>`
- **THEN** the CLI SHALL write the final requested output file under `<dir>`
- **AND** the CLI SHALL report the final output path under `<dir>`

#### Scenario: Writing a segmentation output to an explicit output directory
- **WHEN** a user runs the CLI for `crisp` or `fuzzy` with `--output-dir <dir>`
- **THEN** the CLI SHALL write the final requested segmentation output file under `<dir>`
- **AND** the CLI SHALL report the final output path under `<dir>`

### Requirement: CLI cache directory remains separate
The CLI SHALL treat `--brainweb-dir` as the native BrainWeb cache/download directory, not as the final output directory.

#### Scenario: Using separate cache and output directories
- **WHEN** a user runs the CLI with `--brainweb-dir <cache-dir>` and `--output-dir <output-dir>`
- **THEN** native BrainWeb cache artifacts SHALL be read from or written under `<cache-dir>`
- **AND** the final requested output SHALL be written under `<output-dir>`

#### Scenario: Reporting final output rather than cache artifacts
- **WHEN** a CLI command creates or reuses native cache files while producing a final output
- **THEN** the CLI SHALL report the final requested output path
- **AND** the CLI SHALL NOT report a cache artifact path as the primary saved output

### Requirement: Consistent CLI output behavior across product types
The CLI SHALL use the same final output routing behavior for contrasts and segmentations.

#### Scenario: Running T1 and fuzzy commands with the same output directory
- **WHEN** a user runs one CLI command for `T1` and one CLI command for `fuzzy` with the same `--output-dir`
- **THEN** both final requested output files SHALL be saved under that output directory
- **AND** neither command SHALL write a final requested output file to the current working directory unless the current working directory is the selected output directory

### Requirement: CLI default output directory
The CLI SHALL use the current working directory as the default final output directory when `--output-dir` is omitted.

#### Scenario: Omitting the output directory
- **WHEN** a user runs the CLI without `--output-dir`
- **THEN** the CLI SHALL write the final requested output file under the current working directory
- **AND** `--brainweb-dir`, when provided, SHALL continue to control only the native cache/download directory
