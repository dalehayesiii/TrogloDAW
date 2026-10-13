## MODIFIED Requirements

### Requirement: Preserve initial visual and control contracts
The frontend SHALL expose exactly Generation, Library and Vocal FX with TrogloDAW branding and coherent accessible light/dark themes. Generation SHALL keep concise requested inputs and collapsed More Options; detailed clip, reference, FX and storage/model controls SHALL use progressive disclosure. Drafts and selections SHALL survive navigation, with field semantics unchanged.

#### Scenario: Defaults on first load
- **WHEN** a user opens Generation
- **THEN** Number of Generations is two, More Options is collapsed and only the requested generation controls are available

#### Scenario: Visual evidence
- **WHEN** the theme change is reviewed
- **THEN** paired light/dark desktop/narrow screenshots cover all workflows, expanded settings, results, references and key error/setup/save states

## ADDED Requirements

### Requirement: Concise truthful enrichment feedback
Applicable model workflows SHALL show one retained Enrich prompt toggle beside styles. Unknown-profile or missing-support state SHALL be explained using existing Settings without provider/tuning/review controls. Generated additions SHALL not appear in normal results/editor. Fixed-backing mode SHALL hide irrelevant enrichment controls and retain their drafts for returning to model generation.

#### Scenario: Switch workflows
- **WHEN** the user disables enrichment, switches to fixed backing and returns
- **THEN** the model workflow retains off while the backing workflow has no enrichment control/effect

#### Scenario: Missing support
- **WHEN** a configured profile's support is absent
- **THEN** the UI reports its availability truthfully and uses existing setup rather than claiming active enhancement or creating another configuration flow
