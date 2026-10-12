# TrogloDAW Local model setup and measured limits

Generation uses ACE-Step 1.5 Base locally. The Windows installer contains the
browser interface, Python, core DSP and the pinned uv setup tool; it does not
contain model weights. On first launch, Settings offers explicit model setup.
Choose the model folder before installing. By default it is `models` beside the
configured library (Windows: `Documents/MusicMaker/models`). Library and model
storage may use different drives. All provider/runtime caches follow the model
folder. No cloud generation, audio upload or API key is involved.

## Acquisition and retention

`config/model-manifest.json` records exact URLs, revisions, lengths and SHA-256
checksums for music weights, encoder/tokenizer, decoder, separation weights,
speaker assets and upstream inference code. Setup verifies existing files before
reuse, resumes partial HTTP downloads, rejects checksum failures and preserves
existing files with different contents. It activates a model only after all
assets and the isolated locked runtime pass verification and an offline import
probe. Canceling or failing an optional installation retains the working choice.
Generation disables Hugging Face/Transformers networking and upstream implicit
model acquisition. Runtime dependencies are pinned in `pyproject.toml`/`uv.lock`;
setup creates a temporary hashed export and installs Windows CUDA wheels into the
chosen folder. Node is not an installed runtime dependency.

The Base default needs approximately 6.35 GB of music assets plus 0.42 GB of
separation/speaker assets; allow another 12 GB for inference wheels and caches.
Settings also offers the architecture-compatible SFT checkpoint. SFT is not
separately benchmarked. Turbo is excluded because it overrides classifier-free
guidance and would make Style Influence ineffective.

Opening another model folder verifies/reuses its assets. Relocation copies and
hash-verifies the complete folder before changing the preference, retaining the
original recovery copy. Shared co-owner manifests stay associated with the old
root. Do not delete the recovery copy until the new location works. The app
cannot change a library location while an explicit `MM_LIBRARY` override applies.
Uninstall offers **Remove installed model assets**, checked by default. Cleanup
removes only unchanged files recorded as owned by this installation, including
owned runtime/cache files. Other installations' references, externally supplied
files, changed files and unrelated contents are preserved. Libraries remain.
Unchecking the option (silent uninstall: `/KEEP_MODELS`) retains assets. Upgrades
preserve preferences and model files. Setup never recursively deletes the chosen
model root. Manually changed assets require a separate folder or explicit repair.

## Validated configuration

Measured on 2026-10-12, Windows, NVIDIA RTX 3070 8 GiB, driver 617.14, ordinary
desktop/display activity running, Python 3.12, PyTorch 2.7.1+cu128. No dedicated
full-desktop control or physical microphone was needed. Pinned upstream code:
`ca1e85fe9430179831e6bc6be790c332190a3866`; Base checkpoint:
`e432212fec32b8965a14ffa57ae653438d6abd14`; common encoder/decoder:
`19671f406d603126926c1b7e2adc169acbcade22`.

One output at a time, BF16 CUDA/SDPA, CPU and DiT offload, 32 inference steps,
no planner/LM, compilation or quantization. Generation requires 5.5 GiB free CUDA
memory and 12 GiB available system RAM before loading. CPU generation is not a
validated fallback and fails clearly rather than substituting a procedural beat.
Supported requested lengths are 10–120 seconds, with no silent truncation.

| Output length | Whole subprocess | Model generation | Peak CUDA allocation |
| --- | --- | --- | --- |
| 10 s | 29.41 s | 15.19 s | 4.52 GiB |
| 60 s | 47.05 s | 28.84 s | 4.59 GiB |
| 120 s | 44.73 s | 29.94 s | 4.69 GiB |

These are individual observed runs with the clean, locked installed Windows
runtime and outbound socket connections blocked, not calibrated ETA promises.
The pinned checkpoint uses an older misspelled CFG argument; a checked compatibility
adapter maps the runtime parameter explicitly. With the same seed/caption, CFG 8
versus 1 changed waveform RMS by 0.168, Weirdness 50 versus 90 by 0.347, and
male versus female caption guidance by 0.169. This demonstrates active conditioning,
not an objective claim about musical quality or guaranteed vocal classification.
The real browser also completed N=2 with independently cataloged recipes containing
original input, transformed sample assets and placements. The 120-second
run used a parent-and-child RSS sampler and peaked at 11.03 GiB. Earlier RAM
samples measured only the venv redirector and are intentionally excluded. All
120-second audio chunks contained nonzero signal; exported duration matched the
request. Whisper tiny.en research transcription recovered the requested two lyric
lines in both clean 10-second vocal-character examples and their extracted/overlaid
vocal streams. ASR checks demonstrate lyric intelligibility, not reliable singer
identity or an independent listening-quality score. Longer examples repeated the supplied material and
contained recognition/pronunciation variations. Lyrics are passed unchanged and
retained exactly in recipes; acoustic verbatim delivery is not guaranteed.

HDemucs separation plus ECAPA candidate grouping on a generated 10-second lead
completed in 8.20 seconds; an overlay of two generated vocal songs took 5.91 seconds.
Both peaked at 0.67 GiB CUDA allocation and about 1.98 GiB process RSS. With CUDA
hidden, the validated 8-second CPU fallback took 7.25 seconds and 1.81 GiB RSS.
Identity reconstruction maximum error was below 3e-8 on all three examples.
Both lead and overlap examples yielded four time-partitioned candidates despite
only one/two intended lead voices. Candidate count is not a singer count. This
measured fragmentation is why grouping is explicitly uncertain and correctable. Separation uses CUDA
when at least 2 GiB is free, otherwise CPU; groups use CPU embeddings. Singing,
backing voices and overlapping singers may remain together or split into several
candidates. Every candidate is labeled uncertain. Segment correction changes
grouping, not the physical separation of overlapping singers. Solo and remix
previews are necessary before accepting edits. Bypass reconstruction uses the
exact residual `original - extracted vocals`, rather than adding edited voices
on top of a mix containing the original vocals.

## Runtime and asset licenses

The app acquires pinned inference code and model files explicitly after installation.
Upstream [ACE-Step repository](https://github.com/ACE-Step/ACE-Step-1.5/blob/main/LICENSE)
and [Base checkpoint card](https://huggingface.co/ACE-Step/acestep-v15-base) specify MIT; model implementation
files retain their Apache-2.0 headers. [Qwen encoder assets](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) specify Apache-2.0.
SpeechBrain ECAPA assets specify Apache-2.0. Torchaudio/Demucs code specifies BSD/MIT
respectively. Upstream notices remain in installed runtime source/wheels and the
verified archive; inspect each repository/card before redistributing changed assets.
Dependencies and optional weights are separate from the core Windows installer.

Primary sources: [ACE-Step inference](https://github.com/ACE-Step/ACE-Step-1.5/blob/main/docs/en/INFERENCE.md),
[GPU compatibility](https://github.com/ACE-Step/ACE-Step-1.5/blob/main/docs/en/GPU_COMPATIBILITY.md),
[common model card](https://huggingface.co/ACE-Step/Ace-Step1.5),
[ECAPA model card](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb),
[Demucs license](https://github.com/facebookresearch/demucs/blob/main/LICENSE).
