# Proposal

## Why

Every downloaded installer currently has the same name, so users keeping several releases cannot identify their versions locally. Include the supplied build version in the filename while keeping release verification and in-app update discovery coherent.

## What Changes

- Name the default installer and published release asset `TrogloDAW-Setup-<version>.exe`, including `0.0.0` for development previews.
- Match packaging, checksums, manifests, installer smoke tests and release uploads to the versioned filename.
- Discover and verify versioned update assets while retaining support for previously published fixed-name releases.
- Document the one-time manual upgrade needed by older app updaters that only recognize the fixed filename.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `delivery-workflow`: Versioned installer distribution and matching verification.
- `app-updates`: Version-aware installer discovery with historical-release compatibility.

## Impact

Windows packaging and NSIS defaults, semantic-release asset selection and guard, CI preview uploads, Python update discovery, regression tests and maintained installer documentation. No dependency, installed data/configuration or audio workflow changes.
