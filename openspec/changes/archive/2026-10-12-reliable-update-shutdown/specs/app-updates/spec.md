## ADDED Requirements

### Requirement: Bounded idle process handoff
An acknowledged idle Windows update SHALL wait thirty seconds for graceful old-process exit, then MAY terminate only that same validated original executable/start-time identity. It SHALL wait for exit before installation; reused PIDs or changed executable identities SHALL fail safely.

#### Scenario: Stalled idle shutdown
- **WHEN** the acknowledged idle app stops serving HTTP but its original process remains alive beyond the exit deadline
- **THEN** only that validated process is stopped, installation proceeds after exit, and the verified restarted app becomes healthy without leaving an orphaned launcher lock

#### Scenario: Original process identity changed
- **WHEN** the recorded PID now belongs to a different process or executable
- **THEN** the helper does not stop that process or launch the installer

### Requirement: Observable helper recovery and verified restart
Helper failures SHALL retain status/artifacts and serve recovery status on the original local port when available, including failures before installer launch. Successful completion SHALL require restarted application health, compiled frontend and the verified version/source identity within sixty seconds; restart failures SHALL retain local diagnostic logs.

#### Scenario: Failure before installation
- **WHEN** an acknowledged handoff fails before the installer starts and the local port is available
- **THEN** the helper serves retained failure details and recovery guidance so a browser reload does not leave an unexplained wait

#### Scenario: Restart cannot become healthy
- **WHEN** installed files verify but the restarted app exits, fails to serve or reports a different identity
- **THEN** the helper reports failure with retained diagnostics rather than claiming successful reopening

### Requirement: Recoverable missing handoff status
After forty-five seconds without a successful handoff status read, the browser SHALL show actionable unavailable-status feedback while continuing to poll. A later successful read SHALL clear that warning; the verified restarted version SHALL return the page to the app. Reloading during helper failure SHALL show retained recovery status when its listener is available.

#### Scenario: Helper status remains unavailable
- **WHEN** expected listener interruption continues beyond forty-five seconds
- **THEN** the page explains how to reopen or repair the app instead of indefinitely promising automatic return, and polling remains active
