## Purpose
Define the Angular/Tailwind and FastAPI monorepo migration while preserving the initial offline music app's UI and audio behavior.

## ADDED Requirements
### Requirement: Preserve initial visual and control contracts
The frontend SHALL preserve the initial four tabs (AI Producer, Voice FX, Generator,
Mixer/Remix), with Library inside AI Producer, and existing labels, control ranges,
defaults, grouping and layout. It SHALL bundle the same local fonts and match the
captured light-theme appearance. Broader UX redesign SHALL be deferred.

#### Scenario: Defaults on first load
- **WHEN** a user opens Generator
- **THEN** BPM is 90, style boombap, key A minor, bars 8, swing 0, seed -1,
  with drums, bass and chord pad enabled

#### Scenario: Visual evidence
- **WHEN** this migration is reviewed
- **THEN** paired screenshots at matching viewport sizes cover all four tabs,
  overrides, populated library, preview/results, recipes and an error state

### Requirement: Browser functional parity
The frontend SHALL preserve uploads/imports, inbox import, previews/playback,
name/tag/delete operations, effect preview/save, generation, mixing and recipe
loading, producer overrides/progress/results, downloads, refresh and quit.
API operations SHALL call the existing audio engine without changing DSP algorithms.

#### Scenario: Recipe loading
- **WHEN** a saved mix is selected
- **THEN** its voice/music/settings/FX populate the mixer and name gets _remix

#### Scenario: No voice selected
- **WHEN** production is requested without a voice/upload
- **THEN** the original pick-a-voice message appears and no song is created

### Requirement: Audio transport
Audio previews SHALL show waveforms, play/pause, backward/forward seeking,
mute, playback speed and a download action. The saved file SHALL remain unchanged
by playback controls.

#### Scenario: Preview an effect
- **WHEN** Preview runs
- **THEN** result audio can play/download without adding a voice to the catalog

### Requirement: Same-origin local API and worker
FastAPI SHALL serve compiled assets and library/item/recipe/upload/job/media/shutdown
endpoints on the same configured local origin. DSP jobs SHALL use one background
worker and report queued/running/completed/failed states with producer progress.
Media SHALL expose only opaque server-registered file tokens. Browser mutations
SHALL require a custom request header without enabling cross-origin access.

#### Scenario: Running production
- **WHEN** a DSP job is processing
- **THEN** HTTP status/progress requests remain responsive and failures reach the UI

#### Scenario: Browser cross-origin form
- **WHEN** a form posts without the custom header
- **THEN** the mutation is rejected

### Requirement: Self-contained Windows and source launch
The installer SHALL bundle compiled Angular/Tailwind, embedded Python and locked
runtime wheels/ffmpeg without requiring Node, uv or Python separately. Existing
shortcuts, browser launch, config precedence and user-library retention SHALL work.
Source setup SHALL use uv and build Angular with Node before serving it.

#### Scenario: Installed browser workflow
- **WHEN** the installed launcher runs
- **THEN** Python serves the included UI and opens its local browser URL

### Requirement: Monorepo development stack
Code SHALL live under frontend/ and backend/, helper/setup scripts under scripts/,
development config under config/, packaging assets under cicd/ and ordinary docs
under docs/. Standard root manifests/docs and framework-required config SHALL stay
in their conventional locations. Dependencies SHALL use pyproject/uv.lock and npm
workspace locks, with Ruff/ty/pytest and ESLint/Vitest/Playwright checks.

#### Scenario: Reproducible development
- **WHEN** uv sync --locked and npm ci run
- **THEN** developers and CI install the same resolved dependencies
