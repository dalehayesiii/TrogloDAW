# Recovering an interrupted Windows update

An update can stop the HTTP page while the old Python process is still waiting for a disconnected request to finish. Older builds waited indefinitely; their helper then timed out before opening its status listener. The browser kept the Updating page and another launcher could not acquire the old process's lock.

The fix limits HTTP teardown to ten seconds. After an acknowledged idle handoff, the helper allows thirty seconds for process exit, then checks the original executable/start time again before stopping only that process. It waits for verified service/frontend/version/source health after restart and retains diagnostic logs on failure. A missing status listener now produces browser recovery guidance after forty-five seconds; polling continues so a late restart can still return to the app.

## Repair an affected installation

1. Find the exact versioned installer downloaded by the app, under the selected model folder's `cache/<installation-id>/updates/`. The same folder contains `update-plan.json` and `update-status.json`; the plan identifies the existing installation folder. Alternatively download the published installer and its `SHA256SUMS`/`release.json` from the repository's Releases page.
2. Verify the installer SHA-256 against the published checksum and manifest. Keep the existing library/model folders and configuration files; no uninstall or model deletion is necessary.
3. If the shortcut cannot start and there is a stuck `pythonw.exe`, inspect its executable/command line in Task Manager. End only the old TrogloDAW process from that installation after confirming no audio processing or installation is active. Do not stop every Python process.
4. Run the verified installer, choosing the same installation folder. Existing `config.json`/`config.local.json`, external libraries and models are retained. Start the shortcut and check the version in Settings/footer.

The updater that starts an upgrade comes from the currently installed version. An already stuck older updater cannot receive this fix through its stopped service. Install a release containing the fix once with the verified installer; later upgrades use the repaired handoff.

## Diagnostics and validation

Retain `update-status.json`, `update-plan.json` and the verified installer when asking for help. Restart failures retain `restart.stderr.log` and `restart.stdout.log` beside those files. The ordinary app log is `troglodaw.log` in the configured library. Avoid posting personal catalog/audio/configuration or credentials.

Regression coverage uses synthetic temporary libraries: a never-finishing ASGI request proves source shutdown releases its launch lock; the native installed test reproduces legacy unbounded shutdown and verifies the updater fallback, preserved preferences, visible failure status and confirmed restart. Browser coverage simulates prolonged status loss, checks recovery layouts in both themes at desktop/narrow sizes and verifies automatic return when status resumes.
