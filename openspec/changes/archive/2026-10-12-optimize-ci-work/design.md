# Design

## Context

See proposal.md for motivation. CI jobs use fresh runners; compiled Angular assets are already shared. semantic-release must remain the sole version calculator, and final version metadata is injected into NSIS after the preview build gate.

## Goals / Non-Goals

**Goals:** Preserve ordered required checks and final artifact safeguards while avoiding frontend tooling, repeated browser execution and redundant transfers.

**Non-Goals:** Change application behavior, dependency versions, job topology, release eligibility or owner branch-protection policy.

## Decisions

- Keep full Playwright and native upgrade/model-ownership tests in Windows build. Linux integration keeps CLI/producer and spec/release checks; removing its UI artifact download and browser installation follows from removing duplicate browser tests.
- Add a ReleaseSmoke switch to the existing installer test helper. It checks registry version before launching embedded Python, polls the health endpoint, requests the compiled UI and its entry assets, and uninstalls. It does not invoke npm, CLI generation, producer generation or the full upgrade/ownership suite. Reusing the install/registry/shortcut cleanup avoids a second independent harness.
- Use npm ci --ignore-scripts --workspaces=false outside Angular. Do not omit devDependencies: root release and test tools are declared there. Keep lock versions and existing npm caches.
- Keep preview installer, checksum and manifest in windows-build. Only main creates/uploads release-payload with payload.tar.gz, and release downloads that artifact alone. Use compression-level: 0 for both compressed artifacts.
- Remove uv lock --check after uv sync --locked; locked sync already enforces freshness. Leave generic dependencies and versions unchanged.
- Add docs/**/*.png and docs/**/*.svg to both maintained path-filter exclusions. The concurrent documentation cleanup deletes review images; its docs title must receive documentation skips without exempting frontend assets or executable configuration. Merge this policy before that cleanup PR and avoid concurrent main publication.

## Risks / Trade-offs

- Linux browser coverage is removed by explicit user request; installed Windows browser coverage remains the merge gate.
- Final release smoke is narrower than full E2E; the checked payload must be reused unchanged, and the release integrity/source guard remains mandatory.
- Root-only install may expose accidental reliance on frontend transitive packages; validate official CLI commands and Windows build in CI before merging.
- Release preparation is not executed by PR events; exercise the same smoke mode against the preview installer in the build job before publishing the workflow.

## Migration Plan

Deliver a CI PR from an isolated main worktree, validate the latest required jobs, coordinate with the concurrent app agent, then squash merge with the validated conventional title. Revert the PR to restore prior execution if needed; never move published version tags.
