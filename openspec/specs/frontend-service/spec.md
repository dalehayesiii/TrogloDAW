# frontend-service Specification

## Purpose

Define TrogloDAW's compiled Angular/Tailwind interface and responsive local FastAPI service, preserving portable audio behavior and task-focused workflows.

## Requirements

### Requirement: Preserve initial visual and control contracts
The frontend SHALL expose exactly Generation, Library and Vocal FX with TrogloDAW branding and coherent accessible light/dark themes. Generation SHALL keep concise requested inputs and collapsed More Options; detailed clip, reference, FX and storage/model controls SHALL use progressive disclosure. Drafts and selections SHALL survive navigation, with field semantics unchanged.

#### Scenario: Defaults on first load
- **WHEN** a user opens Generation
- **THEN** Number of Generations is one, More Options is collapsed and only the requested generation controls are available

#### Scenario: Visual evidence
- **WHEN** the theme change is reviewed
- **THEN** paired light/dark desktop/narrow screenshots cover all workflows, expanded settings, results, references and key error/setup/save states

### Requirement: Browser functional parity
The browser SHALL provide uploads/recordings, local library organization/playback,
selective recipe reuse, source-sample generation, song Vocal FX, downloads, refresh
and quit through Python. Existing catalogs and playable legacy songs SHALL remain
accessible. Existing DSP and CLI operations SHALL remain compatible while new
song inference/editing extends their behavior.

#### Scenario: Recipe loading
- **WHEN** saved creation ingredients are selectively imported
- **THEN** only chosen available fields populate Generation, preserving other draft values

#### Scenario: No voice selected
- **WHEN** lyrics/styles are supplied without audio
- **THEN** model inference creates a song without requiring a vocal upload

### Requirement: Audio transport
Audio previews SHALL show waveforms, play/pause, backward/forward seeking,
mute, playback speed and a download action. The saved file SHALL remain unchanged
by playback controls.

#### Scenario: Preview an effect
- **WHEN** Preview runs
- **THEN** result audio can play/download without adding a voice to the catalog

### Requirement: Same-origin local API and worker
FastAPI SHALL serve compiled assets and library/item/recipe/upload/job/media/shutdown endpoints on the same configured local origin. DSP jobs SHALL use one background worker and report queued/running/completed/failed/canceled states with actual stage/work progress, elapsed time, output counts and evidence-qualified remaining ranges. Media SHALL expose only opaque server-registered file tokens. Browser mutations SHALL require a custom request header without enabling cross-origin access.

#### Scenario: Running production
- **WHEN** a DSP job is processing
- **THEN** HTTP status/progress requests remain responsive and failures reach the UI

#### Scenario: Browser cross-origin form
- **WHEN** a form posts without the custom header
- **THEN** the mutation is rejected

#### Scenario: Follow ongoing work
- **WHEN** the UI navigates/reloads during a costly operation
- **THEN** existing job IDs expose current stage/elapsed/count/estimate information and acknowledged terminal results without duplicate submission

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

### Requirement: Task-focused accessible workflows
Each primary tab SHALL have a clear current task/selection and primary action. Empty, loading and error states SHALL explain next steps. Help SHALL work with keyboard/tap as well as hover. Infrequent setup SHALL use a compact settings dialog/drawer without an extra primary tab or normal-form diagnostics.

#### Scenario: First-use task
- **WHEN** a user records/uploads clips, generates, organizes/reuses a song, edits a vocal group or chooses storage
- **THEN** they can complete the flow through labeled controls without developer documentation or manual config editing

### Requirement: Nested input clip adjustments
Input Audio SHALL contain an initially collapsed, clearly named Clip adjustments disclosure for each selected clip. It SHALL explain and expose existing pitch, speed/stretch, volume and replacement choices within the Input Audio widget rather than adding a separate task panel. Adjustments SHALL remain available to uploaded, recorded and prior-song clips because they affect every input source. Existing draft/recipe settings and explicit prior-song preset decisions SHALL be preserved.

#### Scenario: Adjust a recorded clip
- **WHEN** a recording is accepted and Clip adjustments is expanded
- **THEN** the user can change that clip's existing pitch, speed and volume before arrangement without adding a new workflow or changing other clips

#### Scenario: Default input disclosure
- **WHEN** a clip is added to Input Audio
- **THEN** its audio preview/actions are visible and Clip adjustments is closed until requested

### Requirement: Applicable audio arrangement controls
Generation SHALL place collapsed Clip adjustments and arrangement controls inside Input Audio. Mix samples after generation SHALL be available with selected clips; Audio adherence SHALL be available only when conditioning is supported and active. Labels/help SHALL explain full-arrangement conditioning versus post-generation mixing and acknowledge that conditioned samples can change.

#### Scenario: No audio selected
- **WHEN** Input Audio contains no clips
- **THEN** arrangement controls do not present interactive tuning for absent audio

#### Scenario: Choose postmix
- **WHEN** a user opens Input Audio settings and enables Mix samples after generation
- **THEN** Audio adherence is inactive, the choice persists across navigation/reload and the interface explains the selected behavior

### Requirement: Current frontend and service namespace
Current Angular component selectors, browser draft keys, same-origin mutation header and health identity SHALL use the TrogloDAW namespace consistently with installed/source runtime tooling.

#### Scenario: Mutate through the current UI
- **WHEN** the renamed compiled UI submits a job
- **THEN** its X-TrogloDAW-Request header is accepted by the local service while cross-origin/missing-header requests remain rejected

### Requirement: Explain automatic sampling and output
Input Audio SHALL identify its displayed clips as original sources and explain automatic smaller-sample selection, individual transformation and full-song guide arrangement. Generation results SHALL have a clear Song generation output heading with actual song titles distinct from that functional label. Existing layout/controls SHALL remain without requiring users to manage derived samples.

#### Scenario: Understand input and output
- **WHEN** a user previews an input and receives a generated song
- **THEN** help distinguishes original inputs from automatically derived samples and the results area identifies song output independently of any song title

### Requirement: Simple initial setup and Settings folder workflow
Initial setup and Settings SHALL share clearly labeled model/library folder controls. On Windows an explicit Choose folder action SHALL open a native directory picker, display the selected location and leave it unchanged on cancellation. Unsupported source platforms SHALL offer an explicit manual-path fallback. Existing managed data SHALL trigger clear Move existing data, Use folder without moving and Cancel choices when selecting another folder.

#### Scenario: Change a detected default location
- **WHEN** a different model/library folder is selected while data exists in the default/current folder
- **THEN** the user chooses whether to move that data before the app changes its location, using the same workflow during initial setup or later Settings

#### Scenario: Install after folder selection
- **WHEN** a model folder is selected
- **THEN** one distinct Install or verify action uses that destination and preserves elapsed time, actual-byte download time remaining and separate verification/runtime readiness status
