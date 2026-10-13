## 1. Installer behavior

- [x] 1.1 Preserve existing same-directory shortcuts and create missing/changed-directory targets; verify the NSIS branch and native regression assertions.
- [x] 1.2 Extend native tests for user customization, file identity, missing-link repair, changed-target repair and updater preservation; verify PowerShell parsing locally and actual installers in required CI.
- [x] 1.3 Document shortcut reuse and its limits; verify development/update guides match the implemented guard.

## 2. Validation and delivery

- [x] 2.1 Run local project checks and PowerShell parsing; retain actual shortcut policy regression in required installed Windows CI.
- [x] 2.2 Validate the change and sync canonical specs; verify strict spec checks.

## Workflow follow-up

- Archive after local checks and sync, then verify the archived result before opening the implementation PR.
- Monitor all five required CI jobs and squash merge only after the latest revision passes and is current with main.
