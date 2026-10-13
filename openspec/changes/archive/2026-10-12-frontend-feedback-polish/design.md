# Design

## Context

The first audit added feedback to an existing local-link control. The user's review now asks to remove that confusing control entirely. Success toasts are fixed to the page's right edge, with a sticky foreground-dialog variant. Create folder directly follows a block input without separation.

## Goals / Non-Goals

Keep useful download/playback actions and existing notification lifetime/dismissal. Refine the requested placement and spacing without redesigning the app or changing folder persistence.

## Decisions

- Delete the copy control, handler, clipboard tests and obsolete styles, rather than preserving an invisible or ambiguous action. Reclaim its header space for the audio title.
- Use a fixed bottom-center page toast with explicit intrinsic width and a viewport maximum. Reset transforms/insets for the sticky dialog variant and center it within its container.
- Add 12px margin above Create folder without changing label-to-input spacing.
- Exercise folder creation against the temporary real library and measure both page/dialog toast placement at desktop/narrow widths in both themes. Preserve the existing eight-second expiry and dismiss behavior.

## Risks / Trade-offs

- Centering a fixed toast can shrink it to half the viewport if its width remains auto → use max-content width with the existing viewport cap and wrap long text.
- A page translation can offset the dialog toast → explicitly reset the transform for the foreground variant and verify its bounds.
