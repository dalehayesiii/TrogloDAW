# Error and notification policy

TrogloDAW keeps failures readable until the user dismisses them or starts another
attempt in the workflow that produced them. An error never expires on a timer.

| Feedback | Presentation and lifetime |
| --- | --- |
| New success | Existing polite, dismissible notification; expires after eight seconds. Saved results stay in the library. |
| Running or queued job | Foreground progress card with actual timing and cancellation. Never dismissible. |
| Failed or canceled job | Persistent card with actual message, elapsed time, output counts and Dismiss. No duplicate global banner. |
| Request, microphone or validation error | Persistent scoped error with Dismiss. It survives navigation and reload. |
| Historical terminal notices | Newest visible per workflow; earlier notices remain in a counted disclosure. Reconnecting does not announce them as new events. |

Starting a new attempt acknowledges earlier terminal notices in that workflow.
It does not dismiss active work or unrelated errors. These are presentation
acknowledgments: backend job history, timing, partial results, files and recipes
are unchanged. Dismissing a failed batch does not delete its successful songs.

## Workflow boundaries

Song generation and lyric writing are separate. Vocal preparation and rendering
share Vocal FX. Model installation and storage changes are separate. Upload,
recording and input selection share Input Audio. Folder creation, organization
and deletion each have their own scope; library previews/reference selection
share Library. App updates, shutdown and connection failures have their own
scopes. Unknown future job actions default to their action name; `lyrics_generate`
already maps to Lyrics. New direct operations must explicitly identify their
scope when reporting errors and starting retries.

The same notice appears in the foreground page or open dialog. Opening a dialog
or switching tabs does not acknowledge errors. New failures use alert semantics;
active progress and cancellation use polite status. Historical restoration has
no live role, preventing old failures/successes from being announced as new.
Dismiss buttons support keyboard access and return focus to the current tab or
dialog controls when their notice disappears. Color reinforces the text state.

Acknowledgments and ordinary errors use versioned browser storage on the local
origin. A full successful job snapshot prunes acknowledgments for job IDs no longer
held by the backend. Browser storage blocked/cleared, a different browser, or a
changed local origin cannot preserve these presentation preferences; the current
session still supports dismissal. Backend job retention is not extended.

Installer handoff and recovery screens remain blocking application states with
recovery instructions. Acknowledging a notification does not mark an installation
as successful or bypass its recovery process.

## Primary guidance and project decisions

[W3C WAI: Understanding status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
explains how appropriate roles expose dynamic feedback without moving focus,
including success, progress and error messages. It also cautions against an
interface becoming excessively chatty. This supports a single announcement per
failure and silent historical restoration.

[Carbon: Notifications](https://www.carbondesignsystem.com/building-blocks/core/patterns/notifications)
distinguishes persistent inline/actionable feedback from transient informational
toasts, recommends relevant contextual placement, and describes grouped history
as a way to retain notices without crowding the page. These ideas inform the
persistent error cards and expandable earlier notices here.

The exact workflow boundaries, retry acknowledgment, browser persistence and
existing eight-second success duration are TrogloDAW product decisions, not WCAG
requirements or durations mandated by Carbon. Sources checked 2026-10-12.

## Synthetic review evidence

The real local service received three invalid synthetic song-generation requests.
No model download, personal audio or production library was used. Before/after
images use the same retained backend jobs; presentation changed without deleting
those records.

- Before: [light](notification-evidence/before-light.png), [dark](notification-evidence/before-dark.png)
- After: [light](notification-evidence/after-light.png), [dark](notification-evidence/after-dark.png)
- Foreground dialog: [light](notification-evidence/dialog-light.png), [dark](notification-evidence/dialog-dark.png)
- Narrow: [light](notification-evidence/narrow-light.png), [dark](notification-evidence/narrow-dark.png)

Unit tests cover acknowledgment persistence, retry isolation, active protection,
represented-error deduplication and storage failure. Real-backend browser tests
cover failed folder retries, manual dismissal, retained API history, silent
reload, microphone denial and themed/narrow dialog accessibility. Existing setup
fixture tests exercise queued/running cancellation without external downloads.

Windows PR CI runs this browser suite against the packaged installed app, followed
by native upgrade/model-ownership checks. Those registry/installer checks are
reserved for the isolated CI runner while the user’s installed app is active.
