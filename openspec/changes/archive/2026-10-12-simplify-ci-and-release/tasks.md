# Tasks

## 1. Standard CI tools and ordering

- [x] 1.1 Replace custom PR policy with maintained title/path actions, use released action tags and native job dependencies, run Python/Angular in parallel then integration/specs; verify actionlint and docs/failure conditions and document the graph/tool choices.
- [x] 1.2 Remove custom policy code/tests and release planning, share compiled Angular artifacts between jobs, configure dependency caches/Dependabot; verify no stale references or repeated builds and locked dependency checks.

## 2. Windows build and semantic publication

- [x] 2.1 Adapt existing staging to Windows/Git Bash and combine packaging/installed tests in one build job; verify shell syntax and local staging, keeping source setup compatible. The workflow follow-up verifies the clean CI Windows build.
- [x] 2.2 Use official semantic-release exec preparation with the checked payload, fix changelog dependencies and include all commit types, guard published tag history and artifacts; verify release-note and guard tests and document recovery.

## 3. Integrated validation

- [x] 3.1 Run local Python/frontend/integration/spec checks and validate the change; verify passing results and document the remaining custom-script contracts.

## Workflow follow-up

- Sync canonical delivery specs, archive the completed change and validate archive hygiene in this PR.
- Update and push PR #2, monitor GitHub until all five checks pass; leave it unmerged for the user.
