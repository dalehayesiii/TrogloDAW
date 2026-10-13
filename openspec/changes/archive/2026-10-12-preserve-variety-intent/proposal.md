## Why

Variety currently appends instrumentation and song-form instructions regardless of the request. This can contradict speech, a cappella, solo-instrument and sparse requests, undermining the user's explicit constraints.

## What Changes

- Replace forced acoustic accents and song sections with bounded performance variations that explicitly defer to the requested sound sources, delivery and form.
- Preserve literal styles and lyrics, deterministic selection, the zero setting and original/effective recipe provenance.
- Publish the separate prompt-enrichment investigation and its failed preservation gates without enabling unsupported automatic rewriting.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `song-generation`: bounded prompt variety respects the requested instruments, form, vocal delivery and exclusions.

## Impact

Backend parameter construction, synthetic regression tests and documentation. No new model assets, runtime dependencies, settings or catalog migrations. Existing rendered songs and saved effective parameters remain intact.
