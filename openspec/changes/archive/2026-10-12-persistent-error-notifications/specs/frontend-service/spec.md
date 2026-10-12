## ADDED Requirements

### Requirement: Persistent scoped error notifications
Errors and canceled-job notices SHALL remain available until manually dismissed or a new attempt starts in their originating workflow. Retrying one workflow SHALL preserve unrelated notices. Dismissal and retry replacement SHALL persist across reloads on the same origin when browser storage is available. Active jobs SHALL remain visible and SHALL NOT offer dismissal.

#### Scenario: Retry generation
- **WHEN** generation fails repeatedly and the user starts generation again
- **THEN** earlier generation notices are acknowledged while unrelated setup, lyric-writing or library errors remain available

#### Scenario: Dismiss and reconnect
- **WHEN** a failed or canceled notice is dismissed and the browser reloads
- **THEN** that notice stays dismissed without removing backend job history, results or timing

#### Scenario: Active work
- **WHEN** a job is queued or running
- **THEN** its progress remains visible and only cancellation, not dismissal, is offered

### Requirement: One accessible failure presentation
A terminal job failure SHALL have one notification representation instead of a duplicate global banner. New failures SHALL be announced accessibly without stealing focus; restored historical notices SHALL NOT trigger new live announcements. Notifications SHALL remain readable in the foreground page or dialog in both themes. Older retained notices SHALL be expandable within each workflow to bound visible card growth without discarding outcomes.

#### Scenario: Failed job in Settings
- **WHEN** model setup fails while Settings is open
- **THEN** the foreground dialog shows a persistent dismissible job notice with its actual failure text and no duplicate global error

#### Scenario: Multiple historical attempts
- **WHEN** several retained failures exist in one workflow on reconnect
- **THEN** the newest is visible and earlier notices remain available through an explicitly labeled disclosure without replaying old success announcements
