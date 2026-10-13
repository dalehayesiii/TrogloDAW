## ADDED Requirements

### Requirement: Immediate submission busy feedback
Job submission controls SHALL reflect busy state from the start of API acceptance through polling and final refresh. Ordinary processing and model installation SHALL retain their separate busy semantics. Failure SHALL release this transient state without discarding persistent failure feedback. Effect controls SHALL remain editable during FX rendering.

#### Scenario: Render acceptance is delayed
- **WHEN** the user previews a remix and the job submission response is delayed
- **THEN** Preview remix is disabled while effect controls remain editable, and the rendered preview reflects the submitted settings rather than later edits

#### Scenario: Retry finishes before reload
- **WHEN** folder creation retries a prior failure
- **THEN** acknowledgement of old failures occurs at retry start, successful completion produces the normal success notification, and reload after completion does not revive acknowledged failures
