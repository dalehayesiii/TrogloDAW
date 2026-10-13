# Documentation

Start with the [app overview and current screenshots](../README.md). TrogloDAW has
three app tabs—Generation, Library and Vocal FX—and three separate generation
choices inside Generation. The guides below describe current behavior; dated
measurements and before/after captures inside them remain records of those tests.

## Using the app

| Guide | Covers |
| --- | --- |
| [Song workflows](song-workflows.md) | All generation choices, conditioning versus postmix, microphone input, recipes, Library and Vocal FX |
| [Import and arrange over a song](backing-arrangements.md) | WAV import and CPU arrangements over a preserved backing |
| [Model setup and hardware](local-models.md) | Verified downloads, optional models, storage, offline operation and measured requirements |
| [Lyrics, length and musical planning](song-planning.md) | Editable local lyrics, automatic length and internal metadata planning |
| [Guide enhancement](guide-enhancement.md) | Off/Light treatment of sampled conditioning guides |
| [Source-aware sampling](source-aware-sampling.md) | Recording/prior-song roles and bounded automatic arrangements |
| [Style controls and limits](style-adherence.md) | Supported guidance, authoritative text and planner limitations |
| [Library bulk actions](library-bulk-actions.md) | Selection, pagination, folders, deletion and partial failures |
| [Progress and time remaining](progress.md) | Work-based progress, cancellation and local estimate history |
| [Notifications](notifications.md) | Errors, retries and success feedback |
| [Command line](cli.md) | Shared-library commands, procedural synthesis, effects and recipes |

## Install, update and recover

| Guide | Covers |
| --- | --- |
| [App updates](updates.md) | Stable releases, verified installer downloads and private release access |
| [Installation and data recovery](installation-recovery.md) | Reinstall, retained models, portable libraries and rollback |
| [Windows update recovery](update-recovery.md) | Interrupted handoff, restart and occupied-port recovery |
| [Generation recovery](generation-recovery.md) | Repairing drafts affected by the older sampler bug without replacing saved songs |

## Development and delivery

| Guide | Covers |
| --- | --- |
| [Development](development.md) | Source setup, architecture, checks, documentation contributions and packaging |
| [CI and release policy](ci.md) | Job ordering, docs-only exceptions, versioning and publication recovery |
| [Owner repository settings](repository-settings.md) | Squash settings and required checks |
| [Product identity](branding.md) | Current naming, themes and intentional legacy release identity |
| [Canonical specifications](../openspec/specs/) | Maintained application contracts |

## Research and historical evidence

These reports and archives capture the work at the time. They are useful evidence,
not instructions to restore an older UI, runtime or planner:

- [Three-workflow native comparisons](three-generation-workflows.md): current
  contracts followed by the dated 13 October 2026 model experiments and UI review.
- [Sample arrangement before/after validation](sample-arrangements.md): the
  original phrase-planner correction and native conditioning observations.
- [Prompt-enrichment research](prompt-enrichment-research.md): evaluated writers
  and content-preservation limits.
- [Initial frontend usability audit](frontend-ux-audit.md).
- [Dependency audit baseline](dependency-notes.md).
- [Archived OpenSpec changes](../openspec/changes/archive/).

Historical image assets remain in place. New overview screenshots use
`assets/current-*.png`; their capture date and synthetic-fixture limitations appear
in the [overview](../README.md#inside-the-sound-cave).
