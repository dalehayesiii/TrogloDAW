# Design

## Context

See proposal.md for motivation. Library selection currently commits each asynchronous preview response even when another song has been selected. Audio controls discard state on any input change, swallow playback/clipboard errors and use tiny icon targets. FX remix audio persists when settings change; empty pickers and search states lack useful copy. The frontend is compiled static Angular, served by the offline Python service.

## Goals / Non-Goals

Use existing components and API contracts to make visible state truthful. Preserve the three workflows, progressive disclosures and both themes. Limit review to practical usability per the user's direction; keep existing accessibility tests passing without adding a compliance campaign or redesign.

## Decisions

- Give each Library selection a request generation. Clear media immediately and accept only the current response/error. Serialize nothing: users can keep changing selection while a response is pending.
- Synchronize player state with media events, reset transport state only for a changed source, clear old waveforms before decoding and expose playback/clipboard feedback. Local links explicitly remain local; downloads remain the portable sharing path.
- Compare rendered FX settings/segments with current settings using a captured request snapshot. This also detects edits during a pending render without disabling the editing workflow.
- Reuse the existing positive integer count contract (1–32) with nearby feedback and a submission guard. Separate no matches, empty folder and empty library states, with appropriate recovery actions.
- Vendor the upstream playbook and browser-only measurement script at an immutable commit with MIT license. A short project entrypoint and frontend/AGENTS.md apply it to frontend behavior changes. Measurements are leads: spacing heuristics, label-associated targets and decorative artwork are reviewed contextually, never automatic failures. There are no mandatory remote fetches or browser-plugin dependencies.
- Add behavioral regressions to the existing Windows installed-app Playwright path instead of adding a new CI job or checking source patterns.
- Keep service-stopping tests in a dependent shutdown Playwright project. The full run demonstrated the shared service stopped before newly added tests; explicit project dependencies avoid filename-order coupling.

## Risks / Trade-offs

- The upstream measurement script has heuristic false positives and samples a bounded DOM → document limits and confirm findings from actual interactions/screenshots.
- Cached FX results restored across reload may not prove current control equivalence → treat restored previews as last rendered unless a current render proves a match.
- Larger audio hit areas consume space → inspect long names at 390px and desktop widths in both themes.

## Migration Plan

Ship compiled frontend through the normal PR/release pipeline. Existing draft keys and portable audio assets are unchanged; rollback uses the prior frontend. Agent skill discovery takes effect in a subsequent session; current audit reads the installed files directly.
