# Frontend usability audit

Reviewed 2026-10-12 against merged main commit `bceed53`, with fixes in the same PR.
The existing layout and three workflows are coherent. Eight usability findings
were worth repairing; no visual redesign was indicated. The user explicitly
prioritized ordinary usability over accessibility compliance.

## Findings and repairs

| Priority | Location | User consequence | Repair and evidence |
| --- | --- | --- | --- |
| High | `frontend/src/app.ts`, Library selection/preview | Selecting B leaves A's playable audio under B's heading while loading; a slow response for A can overwrite B's preview. A failed load also retains stale media. | Remove previous audio/assets immediately, show loading, accept only the latest selection response and offer Retry preview. Real-service E2E holds A's response until B finishes, then verifies B retains ownership; a current failure/retry is also exercised. |
| Medium | `frontend/src/controls.ts`, audio players | Mute has no visible on/off state. The club-shaped local-link action is ambiguous and appears ineffective. Playback failures are silent; source/label changes can leave displayed transport state inconsistent. Download/copy/mute hit areas were approximately 10×24, 10×22 and 14×24px. | Remove the club/local-link control and its handler/styles; retain download. Show a distinct mute state, explain playback failure and reset stale state only when the audio source changes. Use at least 32px click areas for remaining actions and the speed selector. E2E checks control removal, failures, source replacement, actual mute/rate and clickable actions with a 120-character title at both widths/themes. |
| Medium | `frontend/src/app.html` and `app.ts`, Vocal FX preview | After changing effects, the last rendered remix is still presented without indicating it represents previous settings. An in-flight render can finish after further edits. | Label saved song audio, current FX remix and last rendered FX remix separately; compare controls/grouping to the captured render request. A synthetic cached-song E2E checks edits after a preview and during a delayed render, then verifies a fresh render clears the warning. |
| Low | `frontend/src/app.html`, Library search and pickers | No search matches is described as an empty library. A reference picker can be blank when recordings exist but no songs exist. Empty audio pickers lack a direct recovery action. | Distinguish search, folder and library emptiness, offer clear/show-all/Generation actions, and explain empty picker prerequisites. E2E exercises both empty pickers and clearing an unmatched search. |
| Medium | `frontend/src/app.html` and `app.ts`, Number of Generations | Empty, fractional or out-of-range values can be submitted because the action is outside a native form; validation appears later as a job error. | Show the existing whole-number 1–32 contract beside the field and prevent invalid submissions. E2E verifies four invalid values create zero jobs, then preserves a valid count across reload. |
| Medium | `frontend/src/styles.css`, Library names/headings | A valid 120-character unbroken song name spills outside the song row and preview column, creating horizontal overflow even on desktop. | Wrap long song names/headings within their containers while keeping player labels truncated with a full-title tooltip. The same long-title E2E verifies zero page overflow and clickable audio actions in both themes at 1440px/390px. |
| Low | `frontend/src/styles.css`, success toast | Right-aligned feedback sits away from the visual center of the workflow; page positioning can also affect its foreground-dialog variant. | Center page toasts horizontally near the bottom and dialog toasts inside the dialog, retaining dismissal/expiry. Real folder-creation E2E verifies both placements and bounds in both themes at 1440px/390px. |
| Low | `frontend/src/app.html` and `styles.css`, Create folder | The Create folder button touches the field above it and reads as an attached input segment. | Add a 12px gap above the action. E2E measures the separation in both themes at desktop/narrow widths and exercises actual folder creation. |

## Reusable guard

[`frontend/AGENTS.md`](../frontend/AGENTS.md) and root agent guidance route frontend
interaction/layout/feedback work to the local
[`ui-ux-audit` skill](../.agents/skills/ui-ux-audit/SKILL.md). It asks for a review
proportional to the affected flow, concrete findings, representative themed layout
evidence and meaningful behavior regressions. Backend-only, docs-only and
test-only maintenance do not require a full browser audit.

The full run exposed an existing test-order dependency: Quit stopped the shared
backend before newly added tests could run. Playwright now runs all `app` tests
before its dependent `shutdown` project. The existing Quit assertions moved intact
to `tests/e2e/shutdown.spec.mjs`; future app tests do not depend on filename order.

The upstream [UI/UX audit skill](https://github.com/imYChaudhary22/ui-ux-audit/tree/9db3658b157e4e014f8071810cff6514ab73848a)
was selected because its measurement core runs in an existing browser without
installing another runtime or browser plugin. The upstream playbook is preserved
in `.agents/skills/ui-ux-audit/references/upstream.md`; its unmodified browser
script is `scripts/ui-ux-audit.js`. The MIT license is retained beside the skill.
All three files are pinned to commit `9db3658b157e4e014f8071810cff6514ab73848a`.
The new entrypoint adapts its tool assumptions and priorities to this project.
There is no mandatory remote fetch during future reviews. Skill discovery applies
in the next agent session; the current audit read these installed files directly.

## Review coverage and limits

- Inspected source and rendered Generation, Library and Vocal FX at 1440px and
  390px in light/dark themes, plus Settings, cached vocal groups and stale-preview
  feedback. Both native audio transport and failure paths were exercised using
  synthetic fixtures and temporary storage.
- The measurement script reported zero horizontal overflow across those workflow
  views and no layout-triggering animations. No browser JavaScript errors appeared
  in the rendered audit. The updated player actions were independently checked
  for size, overlap and clickability with long names.
- Spacing/font-count heuristics and 1–2px alignment differences did not expose a
  practical layout defect. The measurement script counts some controls in closed
  disclosures and does not account for label-associated hit areas; these flags
  were not adopted as product requirements. This was not a WCAG compliance audit.
- Local inference/download setup was not repeated for this review. Cached synthetic
  stems cover FX rendering; generation-count submission guards use a ready-state
  fixture without starting model inference. Existing full E2E and installed-app
  checks remain responsible for the broader workflow contracts.
- The reusable skill is guidance, not automatic visual proof. Behavioral regressions
  run in the established Windows installed-app job; subjective flow/layout review
  still needs rendered inspection when the affected UI changes.

Local validation passed: Ruff/format/ty, 168 Python tests, frontend lint/format,
12 frontend unit tests, five release-tool tests, strict Angular build and all 20
Playwright tests. Synthetic CLI demo/producer smoke, skill validation and strict
spec validation also passed. Confirm all five required PR checks on the latest
revision; the PR carries those final installed-app results.
