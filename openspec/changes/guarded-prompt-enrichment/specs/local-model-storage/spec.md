## ADDED Requirements

### Requirement: Independent enrichment support readiness
Explicit model setup SHALL disclose and acquire recommended qualified enrichment support using pinned verification, selected storage, progress, cancellation, relocation and ownership safeguards. Support packages/state SHALL be independently locked and verified. Missing or failed enrichment support SHALL not invalidate a working music installation or trigger downloads during generation/startup.

#### Scenario: Retained music setup
- **WHEN** an update adds an enrichment support profile to an existing verified model
- **THEN** existing music remains ready, first-run setup stays acknowledged and explicit Settings verification reuses existing music assets/runtime while acquiring missing support

#### Scenario: Optional support fails
- **WHEN** enrichment support installation is interrupted or fails
- **THEN** the previous working music model remains usable, owned partials remain recoverable/removable and generation falls back without acquiring files

#### Scenario: Separate add-on dependency graph
- **WHEN** the enrichment codec dependency is added or updated
- **THEN** its separate package target/fingerprint does not change or duplicate an unchanged installed music runtime
