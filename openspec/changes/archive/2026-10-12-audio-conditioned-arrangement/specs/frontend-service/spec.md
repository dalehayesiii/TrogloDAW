# Spec Delta

## ADDED Requirements

### Requirement: Applicable audio arrangement controls
Generation SHALL place collapsed Clip adjustments and arrangement controls inside Input Audio. Mix samples after generation SHALL be available with selected clips; Audio adherence SHALL be available only when conditioning is supported and active. Labels/help SHALL explain full-arrangement conditioning versus post-generation mixing and acknowledge that conditioned samples can change.

#### Scenario: No audio selected
- **WHEN** Input Audio contains no clips
- **THEN** arrangement controls do not present interactive tuning for absent audio

#### Scenario: Choose postmix
- **WHEN** a user opens Input Audio settings and enables Mix samples after generation
- **THEN** Audio adherence is inactive, the choice persists across navigation/reload and the interface explains the selected behavior
