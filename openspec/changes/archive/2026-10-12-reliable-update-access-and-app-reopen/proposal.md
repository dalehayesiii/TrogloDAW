# Proposal

## Why

Update access should reuse a working local GitHub login and provide a browser route for users signed in there. Closing a browser tab leaves the service running, but the launcher only recognizes an existing instance at the default port and can start duplicates during simultaneous launches.

## What Changes

- Discover GitHub CLI from standard Windows installation paths when the desktop process has an older PATH, and fall back to its active login after preferred accounts.
- Offer the latest release in the browser without requiring the backend to read browser cookies, while retaining authenticated verified in-app updates.
- Guard each configuration root with a process-owned lock; reopen only its verified running instance, including alternate ports and concurrent startup.
- Keep work running when a tab closes; Quit stops the service and subsequent launches recover from stale discovery files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `app-updates`: Reliable CLI discovery and browser access fallback.
- `user-interfaces`: Single running app per configuration root and safe reopen behavior.

## Impact

Backend launch coordination, packaged backend payload, credential discovery, Settings update controls, synthetic credential/process tests and maintained documentation. No browser-cookie extraction, stored-data migration or automatic installation.
