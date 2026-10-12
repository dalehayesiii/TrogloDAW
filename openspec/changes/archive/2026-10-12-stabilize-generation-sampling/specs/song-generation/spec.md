## ADDED Requirements

### Requirement: Stable sampling across generation controls
Every exposed Weirdness and Style Influence value SHALL use a validated sampler configuration. Changing Weirdness SHALL not silently select a sampler with an incompatible timestep schedule. Each output SHALL record effective sampler, shift and guidance; existing rendered songs SHALL remain unchanged.

#### Scenario: High Weirdness independent outputs
- **WHEN** a user requests two songs with Weirdness above 50
- **THEN** both use the supported stable sampler sequentially with separate seeds and output assets

#### Scenario: Reuse an affected draft
- **WHEN** a user generates again from a draft saved with the older sampler mapping
- **THEN** the current validated mapping is applied while the previous song and its recorded parameters remain intact
