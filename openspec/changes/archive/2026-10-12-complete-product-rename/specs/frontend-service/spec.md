## ADDED Requirements

### Requirement: Current frontend and service namespace
Current Angular component selectors, browser draft keys, same-origin mutation header and health identity SHALL use the TrogloDAW namespace consistently with installed/source runtime tooling.

#### Scenario: Mutate through the current UI
- **WHEN** the renamed compiled UI submits a job
- **THEN** its X-TrogloDAW-Request header is accepted by the local service while cross-origin/missing-header requests remain rejected

### Requirement: Explain automatic sampling and output
Input Audio SHALL identify its displayed clips as original sources and explain automatic smaller-sample selection, individual transformation and full-song guide arrangement. Generation results SHALL have a clear Song generation output heading with actual song titles distinct from that functional label. Existing layout/controls SHALL remain without requiring users to manage derived samples.

#### Scenario: Understand input and output
- **WHEN** a user previews an input and receives a generated song
- **THEN** help distinguishes original inputs from automatically derived samples and the results area identifies song output independently of any song title
