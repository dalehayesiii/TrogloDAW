## ADDED Requirements

### Requirement: Preview provenance while editing effects
Vocal FX SHALL identify saved song audio or last-rendered audio separately from a preview matching current settings. Changing effects or grouping SHALL make any previous remix visibly stale until a render of the current settings completes. Changes during an in-flight render SHALL not cause that result to be represented as current.

#### Scenario: Adjust effects after preview
- **WHEN** a rendered remix is visible and the user changes gain or another group setting
- **THEN** the interface identifies it as the last rendered remix and prompts Preview remix to hear the current settings

#### Scenario: Edit during a render
- **WHEN** settings change after a remix request begins but before it completes
- **THEN** that output is marked as belonging to earlier settings
