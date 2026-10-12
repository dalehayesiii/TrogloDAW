# Development and delivery

The monorepo has an Angular/Tailwind frontend and a local FastAPI backend.
`backend/mmcore.py` remains the shared DSP/catalog engine; the CLI and HTTP service
both call it. Audio processing is offline and has no model service or API key.
The initial Gradio appearance, four tabs, labels, defaults and workflows are retained.
The library stays inside AI Producer. See [paired screenshots](ui-parity/README.md).

## Layout
| Location | Contents |
| --- | --- |
| `frontend/` | Angular source, static fonts/assets and CLI-required configuration |
| `backend/` | FastAPI service/launcher, CLI, audio engine and Python tests |
| `tests/e2e/` | Playwright functional parity tests against the real service |
| `scripts/` | Development/setup, policy, smoke and Windows build helpers |
| `config/` | ESLint, TypeScript, Prettier, Playwright, release settings and examples |
| `cicd/windows/` | NSIS installer definition and installed runtime launchers |
| `docs/` | Non-OpenSpec documentation and screenshot evidence |
| `openspec/` | Canonical specs and full change archives |
| root | Standard manifests/locks, README and AGENTS.md |

Angular's `angular.json` and `.postcssrc.json` stay in `frontend/` because the CLI
and PostCSS discover them there. Runtime user `config.json`/`config.local.json`
remain at the project/installed app root (or MM_CONFIG_DIR), preserving compatibility;
examples and development config live under `config/`.

## Setup and checks
Install uv 0.13.0 and Node 24.15 or newer. Python 3.12 matches the Windows runtime.
```sh
uv sync --locked
npm ci --ignore-scripts
uv lock --check
uv run --locked ruff check .
uv run --locked ruff format --check backend/app.py scripts backend/tests
uv run --locked ty check
uv run --locked pytest
npm run format:check
npm run lint
npm test
npm run test:frontend
npm run build
npx --no-install playwright install chromium
npm run e2e
npm run specs:check
```
Ruff/ty cover all Python; formatting covers the new service/helpers/tests without
rewriting the original DSP. Frontend checks use angular-eslint, Vitest through the
Angular CLI, strict TypeScript/templates, and Playwright with real audio operations.
E2E tests synthesize a WAV in memory and use a temporary library. Backend tests
cover waveform/recipe equivalence, HTTP uploads/media, producer behavior and shutdown.

For CLI integration tests set MM_LIBRARY to a temporary directory, then run
`uv run --locked python backend/cli.py demo` and
`uv run --locked python scripts/smoke_producer.py`. Never use personal recordings.

`pyproject.toml` declares runtime/dev dependencies; **uv.lock** pins them across
Linux/Windows. Use `uv add`, `uv add --dev`, and `uv lock --upgrade-package NAME`.
`requirements.txt` is a hashed compatibility export, not an independently edited list:
```sh
uv export --locked --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```
Its 0.0.0 project metadata is a development placeholder, never a release version.
The build exports runtime requirements directly from uv.lock and installs Windows
wheels with hashes. The executable version is supplied by semantic-release.

Source launchers are under `scripts/launchers/` and run locked uv setup. They build
the frontend if absent. Rebuild after frontend edits with `npm run build`, then run
`uv run --locked python backend/app.py`. Alternatively use
`npm run start --workspace frontend` for Angular's dev server/API proxy while Python runs.

## Python API and processing
FastAPI serves the compiled frontend and `/api/` from one localhost origin.
Endpoints cover library, item previews/recipes, multipart uploads, queued operations,
job status, media and shutdown. A single ThreadPoolExecutor runs DSP jobs so HTTP
and progress polling stay responsive. Producer stage messages retain their original
meaning. Media uses opaque tokens and only server-registered files; the API exposes
no arbitrary path download. Mutation requests require X-MusicMaker-Request: 1 and
no CORS is enabled, preventing cross-origin browser forms from modifying the library.
`/docs` offers local API documentation. Host/port/config precedence and browser
launch remain; `--no-browser` suppresses automatic launch. This is a local personal
app, not an authenticated remote hosting service.

## OpenSpec
Refresh the committed, pinned workflows with:
```sh
npm run openspec -- init --tools codex,gemini,antigravity,grok --profile core
```
Codex/Antigravity share `.agents/skills/`; Antigravity has `.agents/workflows/`.
Gemini uses `.gemini/skills/` and `.gemini/commands/opsx/`; official Grok Build
uses `.grok/skills/`. A different hosted Grok bot needs its own file-loading mechanism.
Restart editors after setup.

| Tool | Propose | Apply | Archive |
| --- | --- | --- | --- |
| Codex | `$openspec-propose` | `$openspec-apply-change` | `$openspec-archive-change` |
| Gemini | `/opsx:propose` | `/opsx:apply` | `/opsx:archive` |
| Antigravity | `/opsx-propose` | `/opsx-apply` | `/opsx-archive` |
| Grok Build | `/openspec-propose` | `/openspec-apply-change` | `/openspec-archive-change` |

Normally request the entire lifecycle in one PR: proposal/design/specs/tasks,
implementation, tests, canonical spec sync and archive. CLI equivalents:
```sh
npm run openspec -- new change my-change
# Write artifacts, implement and test, complete tasks.
npm run openspec -- validate my-change --strict --no-interactive
npm run openspec -- archive my-change --yes
npm run specs:check
```
Use `--yes` only for completed, authorized work. CI rejects active changes except
explicitly requested docs-only proposals labeled `openspec:proposal-only`, and
rejects unfinished archived tasks. The initial archive includes the app baseline,
UI migration and delivery setup; canonical specs describe the final implementation.

## PRs and releases
Conventional Commit PR titles become squash subjects. Preserve BREAKING CHANGE
footers in the squash body. Only `docs -> false` overrides semantic-release defaults.

| Type | Bump |
| --- | --- |
| feat | minor |
| fix / perf | patch |
| Code type with ! or BREAKING CHANGE footer | major |
| docs (even a breaking footer) | none |
| Other nonbreaking types | none |

The first eligible release starts at **1.0.0**, with stable vX.Y.Z tags on main.
The original untyped commit was never a release; no fabricated historical tag is added.
Docs PRs may change only root documentation/approved docs and OpenSpec Markdown.
Code, dependencies, workflows and generated agent skills are excluded. Both sides
of renames are checked. Lightweight policy/spec/release-tool tests always report;
valid docs-only pushes skip app checks/builds/tags/releases and do not flush pending
code releases from earlier failed runs.

Other PRs run all Python/frontend checks, build a 0.0.0 preview installer and run
browser parity tests against its installed embedded Python on Windows. On main,
read-only analysis using the same semantic analyzer plans a version; no bump means
no installer/release. Eligible versions undergo all checks/builds/installation tests.
The aggregate Required checks gate rejects failed/cancelled/unexpectedly skipped
prerequisites. Only its successful main run can grant the publisher contents-write
GITHUB_TOKEN. Official semantic-release then verifies version/SHA/checksum and
current main before tagging and publishing the tested installer, SHA256SUMS and
release.json. Main runs are serialized. No npm package or bot comment is published.

Re-run a failed main workflow only while its commit is still main, or merge a repair
PR; the next eligible release includes unreleased commits. If a failure occurs
after tag creation, inspect/repair release assets with owner help; never delete
published tags just to retrigger versioning. Owner-enforced squash/check settings
are required: [repository settings](repository-settings.md).

## Installer
On Linux install NSIS, curl and unzip, then run setup/build commands above followed
by `MM_VERSION=0.0.0 bash scripts/windows/build.sh`. Stable versions come from CI.
NSIS bundles Python 3.12.10, locked runtime wheels, ffmpeg and Angular static files.
The installed app needs neither Python, Node nor uv installed separately. Windows
metadata/Apps & Features use the injected version; library/config locations and
shortcuts retain the original behavior. Static validation fails on invalid wheels,
non-Windows binaries, missing dependencies/DLLs or missing ffmpeg. Windows tests
prove the compiled UI/service and actual audio operations work in the installed runtime.

Potential follow-ups: code signing (installer remains unsigned), stricter typed API
request schemas, bounded/expiring job/media caches, broader Python compatibility,
dependency security maintenance and UX redesign. Song-production/model architecture
is deliberately unchanged.
