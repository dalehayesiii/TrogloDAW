## ADDED Requirements

### Requirement: Bounded HTTP shutdown
The local service SHALL limit graceful HTTP teardown to ten seconds, cancel stalled HTTP tasks after that deadline and then run normal audio/setup-worker and temporary-resource cleanup before releasing the launch lock.

#### Scenario: Disconnected request prevents graceful exit
- **WHEN** Quit or update shutdown encounters an HTTP request that never completes
- **THEN** the service cancels that request after the graceful deadline, closes its workers and releases launch ownership so a subsequent launcher can start
