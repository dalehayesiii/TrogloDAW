# Design

## Context

See proposal.md for motivation. The pinned Base/SFT APIs support src_audio in cover mode and audio_cover_strength, while text2music deliberately discards src_audio. Base's misspelled CFG parameter already needs an adapter; its partial-cover loop also repeats the conditioning switch and expands CFG batches on every subsequent step.

## Goals / Non-Goals

**Goals:** Audible, diverse cuts; individual deterministic variations; shared rhythmic arrangement; real audio conditioning; preserved optional postmix and portable replay.

**Non-Goals:** Learned artistic arrangement, guaranteed exact sample identity after diffusion, true singer isolation, changing lyrics, adding a new model or cloud endpoint.

## Decisions

- Use existing phrase/pitch/tempo analysis plus short-frame energy and spectral diversity for bounded selection. Avoid silent regions and duplicate cuts; budget depends on active material and available duration rather than an unconditional count. Every selected source retains at least one audible contribution. An explicit sample count is a cap, not a requirement to duplicate identical cuts.
- Transform cuts individually with seeded pitch/stretch variation around user clip adjustments, limited energy balancing and edge fades. Use one shared tempo, repeated motifs, section dynamics and bounded overlap rather than independent random positions. Retain settings, decisions, gains and timeline placements.
- Produce a full-duration normalized arrangement WAV. With clips, default to cover conditioning; pass this WAV with unchanged lyrics and effective caption to the local model. Audio adherence controls the fraction of diffusion steps using cover conditioning. The generated result is the whole mix, so do not overlay the arrangement again.
- Preserve a Mix samples after generation toggle. This runs text2music independently and overlays the same improved arrangement. Models without declared audio conditioning fall back explicitly and save requested/effective mode and reason; adherence is inactive there.
- Fix the pinned partial-cover switch in memory only, requiring the exact known function fragment and Base/SFT signature before applying the one-time switch. Do not edit verified weights/code assets. Fail clearly if compatibility cannot be established. Keep the existing CFG alias repair.
- New recipe version 2 retains original inputs, transformed cuts, arrangement WAV and model output. Rerender conditioned songs from the saved model mix; rerender postmix from model audio plus gain-bearing placements. Version 1 retains its exact old semantics. Ingredient reuse retains mode/adherence and can reuse an arrangement explicitly.

## Risks / Trade-offs

- Heuristic arrangement can be musically imperfect → disclose heuristics and offer inspectable arrangement audio and postmix choice.
- Cover generation can change or blur input timbre/words → describe adherence as influence, preserve original clips/sample assets, and avoid identity guarantees.
- Sparse source audio can steer a sparse output → repeated section-spanning motifs with measured 10/60/120-second behavior and an independent postmix option.
- Pinned checkpoint compatibility → narrow fail-closed adapter, small regression fixture and real GPU runs at zero/partial/full adherence, offline socket denial.

## Migration Plan

Additive draft fields default to conditioned mode. Existing recipes are not migrated and remain rerenderable. Deploy only after current branding merges, then validate the complete installer payload and browser interface. Rollback preserves saved audio and recipe files.
