# Design

## Context

Music choices already have readable names. The planner description has a combined bundle name, readiness and bytes, while the manifest associates each music choice with a planner and lyric writer. Voice processing uses fixed HDemucs High and SpeechBrain ECAPA models.

## Goals / Non-Goals

Make identities visible without implying that configured weights are installed. Retain the existing installation actions and shared first-use/Settings template; do not introduce selectors for fixed providers.

## Decisions

- Add role/id/name metadata to the existing library model description. Resolve planner/writer IDs through the selected music model's manifest association; known supported IDs get readable labels and other IDs remain visible through a truthful fallback.
- Expose fixed voice-processing names without adding model-manifest labels, avoiding unnecessary cache invalidation from metadata-only manifest changes.
- Show planner role names immediately beside its independent readiness, and disclose fixed voice models progressively. Music selection/install behavior remains unchanged.
- Verify API metadata follows the configured model association and browser Settings retains names in both ready/not-installed states across desktop/narrow themes.

## Risks / Trade-offs

- Readable labels can drift from runtime support → keep labels beside the model-description code and test the underlying configured IDs; unknown IDs fall back to their actual identifier.
- More setup text can crowd the dialog → use a compact definition list and a collapsed voice-model disclosure, with narrow-layout review.
