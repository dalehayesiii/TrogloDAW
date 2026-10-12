# Design

## Context

See proposal.md for motivation. The build already creates a hashed runtime export
under its work directory and uses it for cross-platform wheel installation. The
root export is merely copied into the payload. Source launchers use uv sync.

## Goals / Non-Goals

**Goals:** Remove duplicate maintenance and installer payload while retaining
locked, hash-verified cross-platform packaging.

**Non-Goals:** Change dependency versions, build platform, release semantics,
runtime layout or audio/UI behavior.

## Decisions

Delete only the tracked export and its payload copy. Keep the temporary export:
it supplies exact versions and hashes to uv's Windows-target installation. Using
uv sync for the staged embedded interpreter would change the established bundle
layout and build mechanism without benefiting this cleanup.

Use uv sync --locked in source recovery/build instructions. Installed users can
repair their embedded dependencies by reinstalling the app; they do not need uv.
Remove the old pandas test-directory cleanup because pandas is absent from the
runtime lock. Update policy test examples to the current manifest and lock names.

## Risks / Trade-offs

- External ad hoc consumers of the unadvertised export must use uv or generate
  their own export; documented repository setup already uses uv.
- A leftover copy command would break packaging; CI builds the installer from a
  clean checkout and tests the installed app before Required checks passes.

## Migration Plan

Ship the removal and updated instructions in one maintenance PR. Revert that PR
if an actual external compatibility requirement is discovered.
