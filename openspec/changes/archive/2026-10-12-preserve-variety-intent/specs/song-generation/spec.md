## MODIFIED Requirements

### Requirement: Bounded prompt variety
Variety zero SHALL preserve original styles exactly. Higher values SHALL produce bounded effective style variations per output without rewriting lyrics. Original/effective styles SHALL be shown and saved. Added directions SHALL defer to requested sound sources, delivery and form, without imposing instruments or song sections. Speech, vocal-only and sparse requests SHALL retain their exclusions; changing seeds alone SHALL not count as Variety.

#### Scenario: Multiple varied songs
- **WHEN** multiple outputs are requested with Variety enabled
- **THEN** each retains its effective prompt, original styles and unchanged supplied lyrics

#### Scenario: Spoken or vocal-only request
- **WHEN** a request specifies speech, no music, a cappella or no instruments with Variety enabled
- **THEN** added variation directions preserve the requested sources and delivery without adding accompaniment, beats or song sections

#### Scenario: Solo or sparse request
- **WHEN** a solo-instrument or sparse request uses Variety
- **THEN** additions remain within the requested sound sources and form without requiring a fuller arrangement or new instrumentation
