# Proposal

## Why

Users currently reinstall releases manually and cannot discover updates from the app. The authorized roadmap adds startup release checks and explicit verified Windows upgrades while keeping song generation and personal audio local.

## What Changes

- Check stable GitHub releases asynchronously at installed-app startup, with a startup-check preference and manual Settings check.
- Offer explicit download, cancellation/retry, verification and idle-only installation with visible version/status.
- Support private-release access through existing GitHub CLI credentials or an optional token saved in Windows Credential Manager; keep credentials out of config, logs and cross-host asset redirects.
- Embed the semantic-release-supplied version/source identity and hand off verified upgrades through a hidden helper outside the installation folder.
- Preserve library/models/preferences and leave source/unsupported-platform upgrade behavior explicit.

## Capabilities

### New Capabilities

- `app-updates`: release discovery, private access, verified downloads, cancellation and safe Windows handoff.

### Modified Capabilities

- `delivery-workflow`: installed version/source identity matches the validated published artifact.

## Impact

Python service/update helpers, Settings/update notices, Windows packaging/version smoke checks and update documentation/tests. No new runtime dependency, repository rename, remote audio generation, manual release tag or local publication.
