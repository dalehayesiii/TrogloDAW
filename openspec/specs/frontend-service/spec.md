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

### Requirement: Full-page Quit confirmation
After acknowledged local shutdown, Quit SHALL replace the entire working interface with an accessible themed confirmation that TrogloDAW has stopped and the browser window can be closed. Recording and playback SHALL stop, dialogs/workflow controls SHALL disappear, and no browser-close permission SHALL be required. Failed or unacknowledged shutdown SHALL preserve the interface with a recoverable error.

#### Scenario: Successful Quit
- **WHEN** Quit receives the local shutdown acknowledgment
- **THEN** the page shows only the stopped confirmation with keyboard focus on its heading and remains readable after the service exits

#### Scenario: Shutdown request fails
- **WHEN** the shutdown request fails before acknowledgment
- **THEN** the working interface remains available with an error and Quit can be retried

### Requirement: Transient dismissible success notifications
New successful operation messages SHALL appear as accessible polite notifications with manual dismissal and automatic expiry after eight seconds. They SHALL remain visible within an active dialog without stealing focus. Errors SHALL remain persistent, and reconnecting SHALL NOT replay historical success notifications.

#### Scenario: Storage updated
- **WHEN** a storage location update completes
- **THEN** its success notification is dismissible and expires without changing the selected location or hiding errors

#### Scenario: Reload after success
- **WHEN** a browser reconnects to completed jobs
- **THEN** existing results remain available without reannouncing their old success messages

### Requirement: Persistent scoped error notifications
Errors and canceled-job notices SHALL remain available until manually dismissed or a new attempt starts in their originating workflow. Retrying one workflow SHALL preserve unrelated notices. Dismissal and retry replacement SHALL persist across reloads on the same origin when browser storage is available. Active jobs SHALL remain visible and SHALL NOT offer dismissal.

#### Scenario: Retry generation
- **WHEN** generation fails repeatedly and the user starts generation again
- **THEN** earlier generation notices are acknowledged while unrelated setup, lyric-writing or library errors remain available

#### Scenario: Dismiss and reconnect
- **WHEN** a failed or canceled notice is dismissed and the browser reloads
- **THEN** that notice stays dismissed without removing backend job history, results or timing

#### Scenario: Active work
- **WHEN** a job is queued or running
- **THEN** its progress remains visible and only cancellation, not dismissal, is offered

### Requirement: One accessible failure presentation
A terminal job failure SHALL have one notification representation instead of a duplicate global banner. New failures SHALL be announced accessibly without stealing focus; restored historical notices SHALL NOT trigger new live announcements. Notifications SHALL remain readable in the foreground page or dialog in both themes. Older retained notices SHALL be expandable within each workflow to bound visible card growth without discarding outcomes.

#### Scenario: Failed job in Settings
- **WHEN** model setup fails while Settings is open
- **THEN** the foreground dialog shows a persistent dismissible job notice with its actual failure text and no duplicate global error

#### Scenario: Multiple historical attempts
- **WHEN** several retained failures exist in one workflow on reconnect
- **THEN** the newest is visible and earlier notices remain available through an explicitly labeled disclosure without replaying old success announcements

### Requirement: Selection-owned Library preview
Library preview audio and assets SHALL correspond to the latest selected song. Switching selection SHALL remove the previous playable preview while loading. Late success or failure for an earlier selection SHALL not replace the current preview or its feedback. A failed current preview SHALL expose a retry action.

#### Scenario: Select another song before loading completes
- **WHEN** song A loads after the user has selected song B
- **THEN** B remains selected and A's audio/assets do not appear under B's title

#### Scenario: Current preview fails
- **WHEN** the current selected song's preview cannot load
- **THEN** the interface explains the failure and offers retry without playing the previous song

### Requirement: Contextual empty states and count validation
Library SHALL distinguish an empty library, an empty folder and no search matches. Empty audio/reference pickers SHALL explain how to add suitable items. Invalid generation counts SHALL receive nearby feedback and SHALL not submit a job; the valid contract remains integers from one through 32.

#### Scenario: No search results
- **WHEN** a search finds no matching songs in a nonempty library
- **THEN** the UI identifies the unmatched search and offers clearing search/filters

#### Scenario: Invalid generation count
- **WHEN** the user submits an empty, fractional or out-of-range count
- **THEN** the field explains the accepted range, keeps the draft and prevents a job submission

### Requirement: Contained user-provided names
Song names and headings SHALL remain contained in their workflow columns and list rows at desktop and narrow widths, including valid unbroken 120-character names. Player title truncation SHALL retain the complete title through a tooltip without covering audio actions.

#### Scenario: Long unbroken song name
- **WHEN** the user selects a song whose name is a valid 120-character string without spaces
- **THEN** its name wraps within the list and preview columns without creating horizontal page overflow

### Requirement: Truthful audio playback and download controls
Audio previews SHALL visibly distinguish mute from unmute, reflect the actual playing state and explain playback failure with a recovery action. Changed media SHALL reset stale waveform/time/transport state. Audio sharing SHALL use the download action without a local-link copy control. Small audio actions SHALL have at least 32px click targets and long titles SHALL not overlap those actions.

#### Scenario: Playback rejects an action
- **WHEN** the browser rejects playback
- **THEN** the player displays actionable feedback and remains usable for retry or download

#### Scenario: Change the source
- **WHEN** a different preview replaces the current audio
- **THEN** the old waveform is removed and displayed playback speed/mute/state agree with the new audio element

#### Scenario: Download audio
- **WHEN** the user wants to share a preview
- **THEN** the player offers an audio download and has no ambiguous local-link copy action

### Requirement: Centered success notification placement
Success notifications SHALL be horizontally centered near the bottom of the main page. In a foreground dialog, they SHALL be centered within the dialog and remain readable without overflowing its bounds. Their existing dismissal and eight-second expiry SHALL remain unchanged.

#### Scenario: Page success notification
- **WHEN** folder creation succeeds at desktop or narrow width
- **THEN** its notification is centered horizontally in the viewport

#### Scenario: Foreground dialog notification
- **WHEN** a success notification remains visible while Settings opens
- **THEN** it is centered inside the dialog with no inherited page translation

### Requirement: Distinct folder creation action
Create folder SHALL be separated from the New folder name field by at least 12px so the action reads as a separate button rather than an attached input segment.

#### Scenario: Expanded folder creation
- **WHEN** Create a folder is expanded
- **THEN** the input and Create folder button remain distinct at desktop and narrow widths in both themes

### Requirement: Visible scoped Library selection
Library SHALL initially hide selection checkboxes and batch tools until Select songs is activated. Selection mode SHALL provide independent song checkboxes, a selected count, Select page, Clear selection and Done selecting. Playback preview SHALL remain independent. Selection SHALL include only the current page. Search/folder/page/page-size changes and Done selecting SHALL clear selection; refresh SHALL drop absent or hidden IDs. Tab navigation SHALL preserve selection while its scope remains unchanged.

#### Scenario: Select search results
- **WHEN** the user searches, activates Select songs and selects the page
- **THEN** only visible matches on that page are selected and changing the search clears selection

#### Scenario: Leave selection mode
- **WHEN** the user chooses Done selecting
- **THEN** checked IDs are cleared and checkboxes/batch tools disappear without changing playback

### Requirement: Paginated Library songs
Library SHALL paginate folder/search results with 20 songs per page by default and 10/20/50 page-size choices. Controls below the list SHALL show the current result range, total matches and page count with previous/next actions disabled at boundaries. Search/folder/size changes SHALL return to page one. Refresh after deletion SHALL clamp to a valid page. All matching songs SHALL remain searchable regardless of current page, and other audio/reference consumers SHALL retain the complete catalog.

#### Scenario: Browse and filter multiple pages
- **WHEN** 25 songs match and the user advances from the first page
- **THEN** the remaining five appear with their result range, and a new search returns to page one across the full catalog

#### Scenario: Delete the last page
- **WHEN** the last page's songs are deleted
- **THEN** refresh shows the preceding valid page with updated totals and no hidden selection

### Requirement: Confirmed recoverable bulk actions
Selected songs SHALL offer bulk move and delete. Delete SHALL show the exact count and names in a centered confirmation; cancel SHALL change nothing. Move SHALL offer existing/new logical folders and Unfiled. Duplicate actions SHALL be disabled during work. Success SHALL use an expiring toast; partial failures SHALL show persistent dismissible details and retain failed/unprocessed selections for retry.

#### Scenario: Retry failed deletion
- **WHEN** some songs cannot be deleted
- **THEN** successful songs disappear, remaining selections are preserved, and the Library error identifies failures without claiming complete success

#### Scenario: Cancel confirmation
- **WHEN** the user cancels the bulk-delete confirmation
- **THEN** all selected songs and selection remain unchanged

### Requirement: Immediate submission busy feedback
Job submission controls SHALL reflect busy state from the start of API acceptance through polling and final refresh. Ordinary processing and model installation SHALL retain their separate busy semantics. Failure SHALL release this transient state without discarding persistent failure feedback. Effect controls SHALL remain editable during FX rendering.

#### Scenario: Render acceptance is delayed
- **WHEN** the user previews a remix and the job submission response is delayed
- **THEN** Preview remix is disabled while effect controls remain editable, and the rendered preview reflects the submitted settings rather than later edits

#### Scenario: Retry finishes before reload
- **WHEN** folder creation retries a prior failure
- **THEN** acknowledgement of old failures occurs at retry start, successful completion produces the normal success notification, and reload after completion does not revive acknowledged failures

### Requirement: Bounded HTTP shutdown
The local service SHALL limit graceful HTTP teardown to ten seconds, cancel stalled HTTP tasks after that deadline and then run normal audio/setup-worker and temporary-resource cleanup before releasing the launch lock.

#### Scenario: Disconnected request prevents graceful exit
- **WHEN** Quit or update shutdown encounters an HTTP request that never completes
- **THEN** the service cancels that request after the graceful deadline, closes its workers and releases launch ownership so a subsequent launcher can start
