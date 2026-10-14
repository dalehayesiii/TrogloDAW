## ADDED Requirements

### Requirement: Optional verified phrase detector
Existing model verification SHALL explicitly acquire pinned optional phrase-detection assets into selected model storage. Missing optional assets SHALL not invalidate an already ready music model or require downloads during sampling. Availability and detector identity SHALL be truthful in Settings metadata. Ownership-aware moves, uninstall and shared-file retention SHALL include these assets.

#### Scenario: Upgrade without acquisition
- **WHEN** an upgraded installation retains a ready music model without the new detector
- **THEN** existing generation remains ready and sampling uses a conservative fallback until explicit verification installs the optional asset

#### Scenario: Acquire and reuse detector
- **WHEN** the user invokes existing Install / verify selected model
- **THEN** the optional file is hash-verified or reused with visible acquisition progress and no new provider selector

#### Scenario: Retain changed or shared file
- **WHEN** models are moved or uninstalled and the detector is changed, an unowned custom replacement or shared
- **THEN** existing ownership safeguards retain the file rather than deleting or overwriting it
