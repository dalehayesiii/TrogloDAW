# Design

## Context
See proposal.md. The pinned Base/SFT family exposes ODE and SDE; upstream's default is ODE. Our slider switches samplers implicitly above 50 while also increasing shift. Its SDE branch does not use the shifted next timestep; the user-facing controls have no reason to require that branch.

## Goals / Non-Goals
Restore viable generation throughout the existing slider range, retain independent controls and sequential fresh inference. Do not rewrite checkpoint source, acquire new weights, change saved audio, or claim guaranteed artistic quality.

## Decisions
Use the upstream supported ODE path for all Weirdness values. Shift remains 1–5 and guidance remains independent. Avoid an additional dynamic checkpoint-source patch or an untested sampler threshold. Preserve parameters in recipes so previous runs remain inspectable.

## Risks / Trade-offs
Stochastic sampler variation is removed from new runs; independently selected random seeds and existing Variety remain. ODE does not guarantee a user's desired style; test the reported settings and document the bounded conclusion.

## Migration Plan
No data/configuration migration. Existing audio stays intact. Reusing a creation draft recalculates effective parameters and uses ODE; recipe replay continues playing the original rendered asset. Regenerate an affected draft after updating.
