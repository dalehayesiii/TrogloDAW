# Tasks

## 1. Cleanup reporting

- [x] 1.1 Print removed/retained counts only at the cleanup CLI boundary; verify bounded subprocess output and nonzero unsafe-metadata failure in Python tests.
- [x] 1.2 Add 5,000 synthetic owned cache fragments to native uninstall tests; verify complete removal and shared/unrelated/library retention through the real installer.

## 2. Integration and delivery

- [x] 2.1 Run the documented checks and repeat the native NSIS reproducer with the corrected helper, verifying zero status and bounded output.
- [x] 2.2 Sync the cleanup reporting requirement into canonical local-model-storage and validate all specs.

## Workflow follow-up

- Archive the completed change before opening the implementation PR.
- Monitor required checks, squash merge when current and green, and update WRK-17.
