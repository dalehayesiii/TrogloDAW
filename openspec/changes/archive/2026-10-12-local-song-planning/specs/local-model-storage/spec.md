## ADDED Requirements

### Requirement: Optional verified song planner
Setup SHALL disclose and explicitly install pinned local planner assets into selected model storage using existing verified download, cancellation, relocation and ownership safeguards. Planner readiness SHALL be independently inspectable. A missing planner SHALL not invalidate an otherwise ready music model or trigger a download during inference.

#### Scenario: Retained music model gains planning
- **WHEN** an existing user installs the planner in a retained model folder
- **THEN** complete pinned music/runtime files are reused, missing planner assets are acquired and both capabilities become available

#### Scenario: Planner remains absent
- **WHEN** a user retains a ready music model without installing the planner
- **THEN** explicit-duration music generation remains available and planning actions explain the additional setup requirement
