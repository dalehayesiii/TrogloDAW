# Design

## Context

See proposal.md. Current selection forces one width from the longest uninterrupted above-threshold run, and placement cycles sample indices at almost constant intervals. Source level was present in the actual model guide; simply increasing volume or lowering adherence would conceal the arrangement defect. The pinned cover path follows source structure and can therefore inherit a repetitive guide.

## Goals / Non-Goals

**Goals:** Source-derived mixed-length phrases/accents, occasional complete short clips, musically spaced evolving motifs, safe levels, bounded work/assets and exact portable replay.

**Non-Goals:** Learned composition, guaranteed artistic/model output, word-level alignment, a sample editor, new dependencies, changing lyrics/duration/count controls, or altering the user's current app/library.

## Decisions

- Use robust frame-energy percentiles relative to the source's own level; join brief articulation gaps and respect complete detected phrases. Use mixed phrase/motif/accent candidate widths and time/spectral diversity, rather than shrinking every cut to the shortest activity runs. A seeded subset of eligible short sources includes the entire clip as one transformed sample. Preset cuts still honor their shorter target policy. Silence/DC-only input fails; original files remain untouched.
- Budget distinct source regions from active content and guide length. Create at most three role-based variants per region: recognizable motif, pitch/speed/timbre answer, and shorter filtered fill. These are transformed source waveforms, not synthesized replacement audio. Record cut families/roles, exact effects, peak/headroom scales and sample files. Bound effect tails and attenuate peaks safely after DSP without globally amplifying noise.
- Build sections on a common beat grid. Schedule across intro/body/refrain/bridge/outro with different densities, recognizable limited motif returns, response variants and intentional rests. Plan using actual transformed lengths, separate events with beat-relative gaps, avoid adjacent repetition of the same cut family when alternatives exist and cap both family and exact-variant reuse. Every source and selected family gets a contribution where duration permits; output length always comes from the existing generation parameters.
- Store section, motif, variant and repeat decisions in portable recipe metadata. Render from gain-bearing saved sample placements. Both conditioned and postmix modes consume the same full-duration guide; explicit imported arrangements retain their recorded behavior. Existing songs are not rewritten.
- Keep actual progress units for analysis, derived transforms and rendered arrangement events; version timing-stage complexity so earlier transform-cost observations are not silently reused. No changes to generation count/duration planning owned by concurrent work.

## Risks / Trade-offs

- Short/limited material cannot support unlimited novelty → retain bounded returns and longer rests; describe heuristic limits rather than looping one syllable indefinitely.
- Cover can preserve unwanted sample words/timbre or blur guide differences → expose existing adherence/postmix choice, retain inspectable guide and compare synthetic actual-model behavior without guaranteeing final perception.
- Full clips can dominate → use them only for eligible short inputs, sparingly, and keep accents/phrases as other families.
- Relative detection can admit background noise → reject inaudible/DC input, use bounded balancing/headroom and test quiet scaled sources plus transient-heavy material.

## Migration Plan

New generation records versioned planner decisions. Saved recipes retain their audio/placements and replay unchanged. No storage/config/install migration or new model download is necessary. Rebase onto coordinated current main before opening the complete implementation PR.
