# Design

## Context

The per-user NSIS installer registers its installation directory and writes five known shortcuts unconditionally. Native Windows tests already install twice and exercise the real update helper. See proposal.md for motivation.

## Goals / Non-Goals

Preserve desktop placement and customized shortcut properties during same-directory installs. Keep fresh installs, missing-shortcut repair, directory changes and uninstall cleanup working. Do not scan arbitrary user folders or change Explorer's desktop layout registry.

## Decisions

Read the previous registered installation directory before writing registration. A small NSIS macro skips creation when this directory matches the current directory and the specific shortcut exists. This keeps the shortcut's bytes, timestamps and shell file identity untouched. Missing files are created normally. A changed directory refreshes targets through the existing creation commands.

The native installer test records every shortcut's hash and creation/write times, including a synthetic user description, before reinstall. It checks the same snapshots after both native reinstall and in-app update; then deletes one known shortcut and verifies repair. The test also verifies targets and retains the existing unrelated-entry/uninstall assertions. All test registration and shortcuts remain backed up/restored.

## Risks / Trade-offs

- A user-customized shortcut is preserved on same-directory upgrades, including custom arguments. This is intentional; the app has no shortcut format migration in this change.
- Explorer's visible grid placement cannot be asserted on headless CI. File identity, bytes and timestamps provide direct evidence that the installer no longer replaces the shortcut.
- A moved application directory needs new targets; shortcuts are refreshed in that case. A renamed shortcut outside the known installed paths is not discovered.

## Migration Plan

No configuration or library migration. The next installer reuses existing shortcuts. Normal uninstall still removes the known application shortcuts and preserves unrelated entries.
