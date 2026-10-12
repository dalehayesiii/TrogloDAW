# Agent instructions

## Delivery
- Work on a feature branch and deliver changes through a PR. Never push directly
  to main, create release tags manually, or publish releases locally.
- Use a Conventional Commit title (`feat`, `fix`, `perf`, `docs`, `build`, `ci`,
  `refactor`, `style`, `test`, `chore`, `revert`). Use `!` for breaking code changes.
  `docs:` may contain only documentation and cannot declare breaking changes.
- Run the checks in `docs/development.md`, push, open the PR, and monitor Actions.
  Fix failures until `Required checks` passes on the latest revision. Pending,
  skipped, cancelled, or absent required checks do not count as passing.
- Keep the PR open unless merging is authorized. If authorized, ensure it is current
  with main and all checks pass, then squash merge with the exact validated PR title
  and preserve any `BREAKING CHANGE:` footer in the body. Never bypass protection.
- On Steve's computer use `gh` for GitHub operations, preferring
  `purpledragondude7` when it has access, otherwise `s116821`. Verify identity and
  repository permissions before writes. Use git through PowerShell with profiles
  loaded so the identity hook runs; do not bypass it.
- WRITE access cannot enforce branch protection: report owner setup requirements
  from `docs/repository-settings.md` when needed.

## OpenSpec
- Read `openspec/specs/` and `openspec/config.yaml` before changing behavior.
- Use OpenSpec for app behavior, architecture, dependencies, persistence, packaging,
  CI, or release policy changes. Small typo, formatting, or test-only repairs that
  leave contracts unchanged can rely on the existing specs.
- Normally include the entire lifecycle in ONE PR: create proposal/design/delta
  specs/tasks, implement, test and validate, mark tasks complete, sync canonical
  specs, and archive BEFORE opening the final PR. Commit specs and archive together.
- An explicit user request for the full lifecycle authorizes all phases in one
  task and overrides the generated propose skill's planning-only boundary. Do not
  require a second approval for implementation already authorized by the user.
  If the user requests only a proposal, stop after planning.
- Proposal-only PRs are rare, require an explicit user request, use `docs:` and
  label `openspec:proposal-only`, and explain the reason and follow-up in the body.
  Never apply this label to implementation changes.
- Run `npm run specs:check`. Do not archive unfinished tasks or skip spec sync.
  Specs describe actual behavior and limitations. Tool commands are in the guide.

## Safeguards
- Preserve the Python/FastAPI audio engine and portable catalog paths/saved recipes.
  Angular/Tailwind compiles to static files; Node is development/release tooling only.
- Keep the app offline; remote generation/storage requires an approved product change.
- Use synthetic audio and temporary libraries in tests. Never commit personal audio,
  catalogs, local configs, credentials, installers or caches.
- Manage Python dependencies in pyproject.toml with uv.lock; use uv sync --locked.
  Do not track or ship requirements.txt exports; Windows packaging generates a temporary
  hashed export from uv.lock. Keep CI Python aligned with the embedded Windows runtime.
  Keep release credentials out of PR jobs.
- Keep code under frontend/ and backend/, helper/setup scripts under scripts/,
  development configuration under config/, packaging assets under cicd/, and
  non-OpenSpec documentation under docs/. Root standard manifests/instructions
  and Angular CLI's required frontend/angular.json and .postcssrc.json are exceptions.
- Run Ruff, ty and pytest for Python; ESLint, Vitest, strict Angular compilation
  and Playwright against the real backend for the frontend. Preserve the initial
  Gradio appearance and behavior; any redesign belongs in a separate PR.
- Follow the CI order in docs/ci.md: title gate, parallel Python/Angular, integration
  and specs, Windows build/installed tests, then main-only semantic-release.
  Use maintained tools for generic checks and explicit released action versions.
  Custom scripts must cover documented app-specific contracts. Do not calculate
  release versions independently of semantic-release or rebuild checked frontend assets.
