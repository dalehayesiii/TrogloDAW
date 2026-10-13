## ADDED Requirements

### Requirement: Separate enrichment and requested style fields
Model generation SHALL keep editor/original and per-output Variety styles independent of the enriched inference caption. Accepted enrichment SHALL not rewrite lyrics, title, source assets, duration or authoritative semantic/source inputs. Creation reuse SHALL offer original fields and the explicit enrichment choice, not generated additions as user-authored styles.

#### Scenario: Independent output variety
- **WHEN** one enrichment result serves several independently varied outputs
- **THEN** each retains its own seed/Variety fields and a distinct effective inference caption without changing editor styles or supplied lyrics

#### Scenario: Reuse creation ingredients
- **WHEN** original styles/enrichment choice are reused from an enriched song
- **THEN** the editor receives those original values rather than generated production text
