## MODIFIED Requirements

### Requirement: Observable helper recovery and verified restart
Helper failures SHALL retain status/artifacts. Before verified original-service exit, rejected plans SHALL exit promptly without binding a status listener or launching an installer. After verified service exit, failures SHALL serve recovery on the original local port when available, including before installer launch. Completion SHALL require restarted app health, compiled frontend and verified version/source identity within sixty seconds; restart failures SHALL retain diagnostic logs.

#### Scenario: Failure before installation
- **WHEN** an acknowledged handoff fails after verified original-service exit but before the installer starts and the local port is available
- **THEN** the helper serves retained failure details and recovery guidance so a browser reload does not leave an unexplained wait

#### Scenario: Restart cannot become healthy
- **WHEN** installed files verify but the restarted app exits, fails to serve or reports a different identity
- **THEN** the helper reports failure with retained diagnostics rather than claiming successful reopening

#### Scenario: Rejected preflight
- **WHEN** an installer checksum fails before handoff, whether the configured port is free or occupied
- **THEN** the helper records failure and exits promptly without binding that port, stopping the app or launching the installer
