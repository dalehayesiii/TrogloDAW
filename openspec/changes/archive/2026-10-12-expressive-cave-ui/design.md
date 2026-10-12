# Design

## Context

The initial theme implementation is in the open branding PR and already passes both-theme browser/installed checks. The user wants stronger creative direction and explicitly authorizes an Astra UI pass. The attached image supplies pink/purple and pale lime relationships; existing purple may remain where pleasant/readable.

## Goals / Non-Goals

Goals: recognizably caveman music interface, coherent differentiated hierarchy, useful lime accents, accurate README, understandable nested audio settings and reviewable before/after evidence.

Non-goals: new controls/tabs, audio semantics, new generated raster assets, model changes or redesigning the remaining roadmap's progress/updater behavior in this change.

## Decisions

1. Use code-native cave/stone/rhythm glyphs and CSS geometry across the header, navigation and panels. Build on semantic tokens; keep direct labels, visible focus, sufficient contrast and touch targets. Allocate about one quarter of accent use to pale lime without applying a literal area quota to backgrounds or text.
2. Keep Clip adjustments as an initially closed details dropdown inside each Input Audio clip, with its pitch/stretch/gain/replacement controls and explanatory text. These controls already apply to every source, so all clips may use them. The prior-song preset remains explicit and saved recipes/drafts retain their settings.
3. Test both themes and narrow views with existing real-backend and installed workflows, measure token contrast, and recapture review evidence after the visual pass. Embed old-workflow versus new-theme screenshots directly in the PR body with exact commit references and full galleries.
4. Update the README's current browser capabilities, hardware/setup/storage paths and limits, distinguishing retained legacy CLI behavior from local model generation.

## Risks / Trade-offs

Decorative motifs can reduce legibility, motion comfort or usable space. Keep artwork noninteractive/aria-hidden, avoid unsolicited animation and validate representative overlays/player/keyboard/narrow states. Lime text/control derivatives must meet contrast in both themes. Screenshots use synthetic fixture audio and measured generated results, never personal recordings.
