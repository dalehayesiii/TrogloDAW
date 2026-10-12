# Design

## Context

Packaging, release verification, uploads and the optional updater currently agree on a fixed filename. Semantic-release supplies the stable version; previews use `0.0.0`. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:** Make downloaded versions distinguishable and preserve coherent verified updates.

**Non-Goals:** Change version calculation, install locations, persisted user data or frontend behavior.

## Decisions

- Use `TrogloDAW-Setup-<version>.exe` as the default NSIS output and canonical manifest/checksum filename. Preserve explicit custom build output paths; manifest creation copies those bytes to the canonical versioned name.
- Select versioned release assets with the publisher's supported glob. Before publication, reject missing or multiple matching installers so the glob cannot publish stale versions.
- Installer tests resolve the exact filename from release.json and verify it agrees with its version, rather than selecting the newest file in a directory.
- The updater prefers the exact versioned asset, falling back to the historical fixed name only when the versioned name is absent. Manifest and checksum must match the selected asset. Arbitrary or wrong-version filenames remain invalid.

## Risks / Trade-offs

- Older clients cannot recognize new assets → document a one-time manual verified upgrade; publishing a second fixed-name alias would retain confusing downloads.
- Output directories can contain multiple versions → preview uploads select only `0.0.0`; final release guard refuses ambiguous publication.

## Migration Plan

Merge through the existing checks and allow semantic-release to publish normally. Older clients manually download and verify the new installer, close the app and install into the existing location. Subsequent updates use versioned discovery. Keep previous release assets intact for historical downloads; rollback uses a manually selected known installer, preserving configured library/model folders.
