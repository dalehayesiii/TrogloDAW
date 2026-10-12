# Tasks

## 1. Packaging and publication

- [x] 1.1 Update output defaults, manifests, release uploads/guard and installer smoke resolution; verify synthetic manifest and release guard regression tests and document versioned downloads.

## 2. Update compatibility

- [x] 2.1 Select and verify exact versioned update assets with historical fallback; verify both names, preference and wrong-version rejection in synthetic update tests and document manual transition.

## 3. Integration validation

- [x] 3.1 Run the documented local checks and strict change validation, then sync canonical specs and verify strict spec validation before archive.

## Workflow follow-up

- Archive the completed change and run npm run specs:check.
- Deliver an open PR and monitor all five required Actions jobs on its latest revision.
