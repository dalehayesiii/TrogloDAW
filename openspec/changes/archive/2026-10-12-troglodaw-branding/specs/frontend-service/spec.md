# Spec Delta

## MODIFIED Requirements

### Requirement: Preserve initial visual and control contracts
The frontend SHALL expose exactly Generation, Library and Vocal FX with TrogloDAW branding and coherent accessible light/dark themes. Generation SHALL keep concise requested inputs and collapsed More Options; detailed clip, reference, FX and storage/model controls SHALL use progressive disclosure. Drafts and selections SHALL survive navigation, with field semantics unchanged.

#### Scenario: Defaults on first load
- **WHEN** a user opens Generation
- **THEN** Number of Generations is one, More Options is collapsed and only the requested generation controls are available

#### Scenario: Visual evidence
- **WHEN** the theme change is reviewed
- **THEN** paired light/dark desktop/narrow screenshots cover all workflows, expanded settings, results, references and key error/setup/save states
