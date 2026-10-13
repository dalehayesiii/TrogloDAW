# Proposal

## Why

Machine-specific agent account preferences have leaked into repository instructions and release credential lookup. A portable application must use credentials selected by its user rather than preferred personal usernames.

## What Changes

- Remove installation-specific account and shell guidance from repository instructions.
- Read only the active GitHub CLI login without choosing or switching named accounts.
- Preserve saved Windows credentials, explicit environment tokens, public access, credential discovery and token redaction.
- Replace personal account fixtures and update the credential documentation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `app-updates`: account-neutral release credential discovery.

## Impact

Repository agent guidance, update credential lookup, synthetic credential tests and update documentation. No dependencies or installation/configuration migration.
