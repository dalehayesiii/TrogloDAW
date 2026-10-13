## ADDED Requirements

### Requirement: Explicit whole-vocal FX target
Newly opened songs SHALL default to All vocals instead of an arbitrarily sorted candidate group. All-vocal control changes SHALL update that parameter in every actual voice group; selecting one group SHALL preserve independent editing. Full-vocal solo preview SHALL use the complete unprocessed cached vocal stem. Mixed effective values across groups SHALL be identified without silently overwriting other settings. Existing recipes and candidate assignments SHALL remain compatible.

#### Scenario: First sorted group starts late
- **WHEN** the first candidate group begins after other vocals and the user changes pitch with All vocals selected
- **THEN** vocals in the opening groups and later groups receive that pitch setting, with original segment offsets and accompaniment preserved

#### Scenario: Independent and mixed settings
- **WHEN** one group is edited differently and the user returns to All vocals
- **THEN** differing parameters are marked Mixed, and changing one parameter applies it to every group without changing their other independent values

#### Scenario: Full vocal solo
- **WHEN** All vocals is selected
- **THEN** its solo preview includes all assigned vocal regions rather than starting at the first sorted candidate's onset
