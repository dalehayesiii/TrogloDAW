# Styling adherence: tested controls and limits

TrogloDAW preserves the user's styling text. The Base-family **Style Influence**
control maps to classifier-free guidance 1–15; it is independent of source-audio
adherence and the ODE schedule. Explicit instruments, vocal character, tempo/feel
and production descriptions can communicate intent more precisely, but no control
guarantees genre, voice identity or exact delivery.

The [official inference API](https://ace-step.github.io/ACE-Step-1.5/en/INFERENCE)
documents Base/SFT guidance and schedule parameters. Turbo overrides classifier-free
guidance, so it is excluded from the app's current selector. For audio-guided work,
higher **Audio adherence** follows the supplied arrangement more closely; lower
values allow more deviation. This can compete with text styling rather than improve
it automatically. See the [official guide](https://ace-step.github.io/ACE-Step-1.5/en/Tutorial).

## Research outcome

The upstream [5Hz-4B adherence report](https://github.com/ace-step/ACE-Step-1.5/issues/424)
describes incorrect language, topic and styling in its generated captions/lyrics.
Contributors recommend explicit editable inputs and distinguish the audio-code
planner from a general instruction writer. These reports do not establish a
universally reliable automatic style-enhancement preset.

Our pinned 1.7B planner test at seed 42 expanded a city-pop description coherently,
but rewrote “solo baroque harpsichord, no drums, instrumental” as a flute/piano chamber
piece. Another lyric-bearing test omitted requested drums and added vocal/guitar
details. These are text-planner observations, not an audio fidelity score. Applying
those rewritten captions silently would change user intent. Only validated length
metadata is consumed for automatic duration; original captions and lyrics reach the
music model. Suggested metadata stays in the saved planning provenance.

Existing fixed-seed guidance comparisons changed the resulting waveform, proving
the control is active, but waveform difference alone cannot measure styling quality.
The supported sampler repair and varied-source arrangement correction address
verified implementation faults; they do not promise model-level genre accuracy.

## Future model profiles

The [prompt-enrichment study](prompt-enrichment-research.md) extends this research
with instrumental, speech, vocal-only, sparse and multilingual requests. None of
the tested automatic writers qualified for default-on use. Supplied lyrics remain
literal and original styling remains authoritative. Variety now varies performance
within the requested sound sources and form instead of adding acoustic accents or
song sections to every request; its `requested-performance-v1` identity is saved
with each output's parameters. This avoids an app-created contradiction, without
claiming a measured improvement in the music model's genre fidelity.

Capabilities and optional planner identities belong to each model's manifest entry.
An unexplored model receives no automatic caption enhancement. A future caption
adapter should be explicit per model/revision, preserve requested/effective text in
recipes, and pass a fixed-seed comparison suite covering instruments, genre, language,
negative constraints and audio-guided cases before activation. Editable preview is
preferable to hidden rewriting. No keyword substitution, external generation API,
unverified LoRA or instruction-model jailbreak is introduced by this investigation.
