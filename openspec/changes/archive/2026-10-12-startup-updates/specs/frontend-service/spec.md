# Spec Delta

## ADDED Requirements

### Requirement: Transient dismissible success notifications
New successful operation messages SHALL appear as accessible polite notifications with manual dismissal and automatic expiry after eight seconds. They SHALL remain visible within an active dialog without stealing focus. Errors SHALL remain persistent, and reconnecting SHALL NOT replay historical success notifications.

#### Scenario: Storage updated
- **WHEN** a storage location update completes
- **THEN** its success notification is dismissible and expires without changing the selected location or hiding errors

#### Scenario: Reload after success
- **WHEN** a browser reconnects to completed jobs
- **THEN** existing results remain available without reannouncing their old success messages
