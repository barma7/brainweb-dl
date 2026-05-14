## ADDED Requirements

### Requirement: Structured tissue-property metadata
The system SHALL support a structured tissue-property metadata file for BrainWeb-derived generated maps.

#### Scenario: Loading field-aware tissue properties
- **WHEN** generated BrainWeb20 contrast logic needs tissue parameters
- **THEN** the system SHALL be able to load canonical tissues, download aliases, density weights, field strengths, and per-field tissue properties from package data
- **AND** the metadata SHALL declare units for relaxation-time and density-like values

### Requirement: Canonical tissue alias aggregation
The system SHALL aggregate BrainWeb fuzzy segmentation channels into canonical tissue probability maps according to the configured download aliases.

#### Scenario: Grouping multiple BrainWeb aliases into one canonical tissue
- **WHEN** a canonical tissue lists multiple aliases such as fat-related channels
- **THEN** the generated-map logic SHALL sum those fuzzy channels before applying the canonical tissue density and tissue properties

### Requirement: Density-weighted apparent relaxation maps
The system SHALL generate apparent relaxation maps from fuzzy segmentations using tissue density weights and relaxation-rate or signal-based mixing rather than linear relaxation-time averaging.

#### Scenario: Initial-slope apparent T2 generation
- **WHEN** a BrainWeb20 generated T2 map is requested with the initial-slope method
- **THEN** each voxel SHALL compute tissue weights as `fuzzy_fraction * density`
- **AND** the apparent relaxation rate SHALL be the weighted mean of tissue relaxation rates
- **AND** the apparent T2 SHALL be the reciprocal of that apparent rate

#### Scenario: Two-point apparent T2 generation
- **WHEN** a BrainWeb20 generated T2 map is requested with two echo times
- **THEN** the system SHALL compute mixed signals at both echo times from density-weighted tissue exponentials
- **AND** the apparent T2 SHALL match the mono-exponential log-slope between those two mixed signals

### Requirement: Native BrainWeb T1 behavior remains unchanged
The system SHALL continue returning native BrainWeb T1 image data for BrainWeb20 `contrast="T1"` requests.

#### Scenario: Requesting BrainWeb20 T1
- **WHEN** `get_mri(sub_id=4, contrast="T1")` is called
- **THEN** the system SHALL load the native BrainWeb T1 image rather than synthesize a T1 map from fuzzy segmentation metadata

### Requirement: Documented generated-map scope
The system SHALL document that generated relaxation maps are apparent approximations, not full MRI sequence simulations.

#### Scenario: User reads generated-map documentation
- **WHEN** generated contrasts are described in public documentation or docstrings
- **THEN** the documentation SHALL state the approximation method and its expected limitations
