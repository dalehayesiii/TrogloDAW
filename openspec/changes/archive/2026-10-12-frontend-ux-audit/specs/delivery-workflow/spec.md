## ADDED Requirements

### Requirement: Conditional frontend usability review
Frontend behavior, layout or interaction changes SHALL use the repository-local UI/UX audit skill and record concrete findings, fixes and limitations. Review SHALL be proportional to the affected flow and user priorities, covering normal interaction, asynchronous feedback and representative desktop/narrow themed layouts. Backend-only, documentation-only and test-only maintenance SHALL not trigger a full UI audit.

#### Scenario: Change a frontend interaction
- **WHEN** a contributor changes a frontend flow
- **THEN** frontend-scoped agent guidance routes to the local skill and relevant behavior/layout checks are recorded with the change

#### Scenario: Unrelated maintenance
- **WHEN** a change touches only backend or documentation contracts
- **THEN** the frontend audit skill does not require an unrelated browser audit

### Requirement: Reviewable vendored audit guidance
Vendored audit guidance SHALL retain its license and immutable source provenance. Heuristic findings SHALL be confirmed through rendered evidence or interaction before being treated as defects.

#### Scenario: Automated heuristic flag
- **WHEN** a measurement script flags spacing, a target or another heuristic
- **THEN** the contributor verifies its actual user consequence and records its disposition rather than imposing an arbitrary design score

### Requirement: Ordered browser test lifecycle
Browser tests that stop the shared local service SHALL run after all ordinary app tests through an explicit dependency, so newly added test files do not depend on filename ordering to keep the backend available.

#### Scenario: Add another browser regression file
- **WHEN** a new ordinary app test file is included in the full browser suite
- **THEN** it finishes before Quit stops the shared service
