# Phrase sampling

New sampled-song and preserved-backing arrangements use `phrase-motifs-v4`.
Recording + style still sends one intact source directly to the song model.

The sampler keeps complete detected vocal phrases and chooses pause boundaries
between words/phrases. Uniform windows, phrase thirds and onset cuts cannot cross
protected vocal spans. A phrase can exceed the saved nominal sample-length
preference, including the historical one-second prior-song preset. Sample count
is a maximum, not a quota. Whole phrases must fit the timeline after transformation;
otherwise the error explains longer-duration/fewer-input recovery. Qualified
instrumental regions retain best-effort shorter/onset cuts outside protected vocals.

## Detection and offline fallback

Silero VAD 6.2.3 is an optional verified 2,272,526-byte (2.17 MiB) asset acquired
through **Install / verify selected model**. Older ready music models remain ready
without it; unchanged weights are reused on verification. Settings' **Voice
processing models** disclosure shows its availability. The pinned JIT uses the
existing locked Torch runtime, one CPU thread and no GPU music model. There is
no new dependency or runtime download. CPU-only backing without model setup uses
the acoustic fallback.

Analysis uses a normalized phase-safe copy at 16 kHz in 512-sample frames. Speech
activity uses hysteresis and 320 ms pause confirmation, keeps brief detected words,
and never forces a maximum-utterance cut. Up to 240 ms endpoint context approaches
the midpoint of confirmed pauses without rejoining them. Acoustic fallback joins
gaps up to 280 ms and keeps context around complete activity runs. Original source
assets are never normalized or rewritten by this analysis.

VAD detects activity rather than transcribing words. Singing, breathy consonants,
noise and overlap can confuse it. Uncertain decisions and failed/missing detection
use complete acoustic phrases; an unknown continuous finished mix cannot authorize
shorter cuts or a blind whole-song overlay. These safeguards improve boundary
selection but do not prove universal word recognition. Review new samples when
source quality makes pauses unclear.

Evidence records protected offsets, confidence, detector/source/runtime identity,
selection policy and fallback in the recipe. Valid content/model/version-keyed
JSON caches live under relative `assets/source-analysis/` Library paths and are
reused across outputs. Invalid timestamps/dimensions are recomputed or fall back;
analysis has real frame progress and cancellation. Moving the whole Library keeps
references portable. Existing songs and explicit saved layouts replay without
new analysis or changed cuts. To request new boundaries, start a fresh arrangement.

## Validation on 13 October 2026

The actual pinned CPU detector and implemented analysis/selection path were run
offline on three Windows-synthesized sentences with 500 ms inter-recording pauses,
14.231625 seconds total. Plain speech, speech over a continuous 220 Hz bed, speech
at 0.003 level, added low noise and phase-inverted stereo each produced six
protected phrases (including sentence/clause pauses). A one-second preset kept
each protected phrase complete. For plain speech, selected intervals in seconds
were 0–1.776, 1.776–3.440, 4.336–6.096, 6.448–8.656, 9.520–11.712 and
11.712–13.264. These are detector decisions on invented audio, not manual linguistic
annotations or listening scores.

A pure 220 Hz instrument tone qualified as instrumental and retained shorter
cuts. All six cases processed 445 frames on CPU with outbound socket connections
blocked; source copies and selection never crossed protected spans. In a single
process the first case took 3.64 seconds including Torch import, then 0.44–0.53
seconds per case. These warm-process measurements exclude source decode outside
the analysis action and do not establish fresh-subprocess user ETAs, singing
quality, all languages or model song quality. Tests additionally cover brief words,
long uninterrupted spans, invalid cache evidence, model changes, cancellation,
all eight source collections, original assets and relocated historical replay.

A further native probe placed one quiet synthesized utterance at 10 seconds in
an otherwise silent 63-second recording. Using the whole-file percentile alone
left analysis gain at 1 and delayed the protected start to 10.256 seconds.
Normalizing the audible portion of the analysis copy instead kept the start at
9.968 seconds and identified the internal clause pause, yielding protected spans
9.968–11.792 and 11.792–13.456. The detector remained on CPU and the saved source
bytes were identical before and after. This bounds a sparse-input onset regression;
it does not establish universal word alignment.

Primary source: [pinned Silero VAD revision](https://github.com/snakers4/silero-vad/tree/5cd7945676eb32225748052e2e6a0580e4686a08),
[MIT license](https://github.com/snakers4/silero-vad/blob/5cd7945676eb32225748052e2e6a0580e4686a08/LICENSE).
Asset SHA-256: `e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720`.
No upstream helper code or synthetic/private audio is committed.

## Compiled-app review

The affected input help and Settings disclosure were reviewed against the real
temporary-library service at 1440 px and 390 px in both themes. The old “varied
smaller cuts” guidance was misleading for vocals (minor usability issue): it now
explains complete phrases, shorter instrument cuts and longer uncertain material.
Optional CPU readiness and the existing verification action are visible in the
model disclosure without new controls. No horizontal overflow was observed;
the existing Settings dialog scrolls to its lower content. Closing it preserves
the edited lyrics draft. Browser regressions check the missing-detector message,
verification action, retained draft and intact-source mode guidance. No download
or GPU generation was performed in this UI fixture.
