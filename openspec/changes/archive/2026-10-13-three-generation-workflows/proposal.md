# Proposal

## Why

Sampling a collection, arranging over an existing backing, and reinterpreting one intact recording have different audio contracts. The current interface exposes only the first two, defaults sampled generation to independent postmix, and never uses the installed music planner to produce semantic blueprints.

## What Changes

- Offer three Generation choices with preserved drafts: sampled song generation, the existing fixed-backing arrangement, and one intact recording plus style without lyrics or Library/reference inputs.
- Default fresh sampled generation to arrangement conditioning; retain an optional postmix checkbox, explicit saved choices, and truthful hover/focus/tap guidance.
- Validate supported direct-recording lengths and source-vocal behavior with the pinned runtime; do not silently slice, overlay, or force instrumental output.
- Automatically use verified musical metadata blueprints for compatible text-driven generation when installed. Native comparisons rejected semantic-code blueprints for lyric drift. Keep actual source audio authoritative in conditioned modes; disclose internally why planning is used, bypassed, unavailable, or failed.
- Evaluate Remiqora-inspired source context/complementary generation mechanisms without adding a DAW editor, rewriting supplied text, or assuming an unsupported source-plus-blueprint combination.
- Preserve portable sources, blueprint/model provenance, historical replay, independent outputs, offline runtime, and sequential memory safeguards.

## Capabilities

### New Capabilities

None; these are extensions of existing song generation and model setup.

### Modified Capabilities

- `song-generation`: three workflow contracts, conditioning default, direct recording generation, internal capability-aware planning and reusable provenance.
- `local-model-storage`: identify supported blueprint planning using the existing optional verified planner and independent readiness.

## Impact

Generation UI/draft persistence, FastAPI validation/progress, song orchestration, the isolated inference adapter, model capability metadata, tests and workflow/model documentation. WRK-9 source routing and WRK-25 backing preservation are reused from merged main. No remote services, dependency changes, new primary tabs, data migration, or mandatory downloads are intended.
