## Context

WRK-5 retained legacy names for compatibility; the user explicitly reverses that policy because there are no active users. WRK-11 now produces content-aware samples and a single conditioning arrangement with a postmix alternative. This separate PR completes naming and improves descriptive copy without new sample-management UI.

## Goals / Non-Goals

Goals: complete current TrogloDAW namespace, one release artifact, unchanged audio behavior/model runtime graph, clear original-clip versus generated-sample/output descriptions and native proof.

Non-goals: renaming the actual GitHub repository without its owner's separate action, rewriting historical archives/screenshots, changing model weights or algorithms, adding user-managed generated samples or continuing compatibility aliases.

## Decisions

1. Use TrogloDAW default Windows install/Documents roots and registry keys, troglodaw.nsi/icon/VBS/console assets, troglodaw CLI wrappers, troglocore Python module, TROGLODAW_* environment variables, X-TrogloDAW-Request and health application=troglodaw. Angular selectors/draft key and package/project metadata follow the namespace. Keep catalogs, recipes and user-selected external libraries/model folders intact; no automatic old-install migration is promised.
2. Publish only TrogloDAW-Setup.exe with one SHA256SUMS line and no legacy_installer metadata. Keep semantic-release as sole version authority and validate the actual artifact/version/source/checksum before publication. Change the project package names using locked tooling and prove the inference graph fingerprint is unchanged.
3. Delete old-shortcut migration/test assertions; retain ownership-safe model removal, user-data safeguards, known shortcut cleanup and same-name TrogloDAW upgrades. Native tests back up/restore only the current registry/shortcut names and verify the renamed CLI and installed browser.
4. Clarify that Input Audio previews are originals; selected smaller samples are generated/transformed/arranged automatically into a guide. Clip adjustments are baseline settings for derived samples. Keep the layout and original functional labels. Add a fixed Song generation output heading and show each actual title beneath it; use human-readable demo titles in new review evidence.
5. Mark the PR refactor! and preserve its BREAKING CHANGE footer through authorized squash merge. Sync/archive contracts in the same PR; current documentation lists only new namespaces. Existing before evidence/archives remain historical and external source links continue to point to the real remote.

## Risks / Trade-offs

The README reuses vector paths from the actual UI rather than adding a second visual identity. Dark-only screenshots show real conditioned generation and live extraction from synthetic demonstration input; no personal audio or model assets are committed. Keep setup, hardware limits, CLI and developer instructions accessible below the visual overview.

Cross-language launch/import/header/environment names must change together. Broad text edits can accidentally change actual repository links or duplicate canonical paths; review those explicitly and verify native installed flows/checksum guards. Renamed local project metadata must not invalidate an otherwise identical multi-gigabyte inference environment.
