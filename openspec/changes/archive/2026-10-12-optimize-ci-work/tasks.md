# Tasks

## 1. CI and installer validation

- [x] 1.1 Keep full browser tests only in Windows build and implement focused ReleaseSmoke mode; verify PowerShell parsing and smoke against a released EXE locally, and configure the required build job to run the full installed suite and smoke against the preview EXE.
- [x] 1.2 Install root npm tools outside Angular, separate main-only payload and disable Windows artifact recompression; verify root-only npm tests/OpenSpec commands and workflow lint.
- [x] 1.3 Remove redundant uv lock --check, classify docs PNG/SVG assets in both filters and update CI/development/agent instructions; verify documentation matches execution, root formatting and Python checks pass, and image-vs-code path filtering passes.

## 2. Delivery validation

- [x] 2.1 Validate the OpenSpec change and local checks, sync the canonical delivery spec, and verify strict spec validation before archival.

## Workflow follow-up

- Archive the completed change in this implementation PR, verify archived specs and completed tasks.
- Open a conventional CI PR, validate all five required checks on the latest revision, coordinate main merge timing with the concurrent agent, then squash merge as authorized.
- Verify main CI and semantic-release complete without repeating full browser tests or changing version rules.
