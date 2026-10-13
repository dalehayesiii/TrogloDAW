## Context

See proposal.md. Parameter construction selects one to three phrases by seed and retains original/effective styles. The phrases currently name acoustic sounds, a chorus and a bridge. The prompt-enrichment research also shows that a generic instruction writer can violate explicit constraints.

## Goals / Non-Goals

Preserve the bounded deterministic Variety control while removing instructions that impose an instrument or musical form. This change does not claim to improve ACE's underlying genre fidelity or implement the rejected default-on text-rewriting candidates.

## Decisions

Use six source-neutral directions for dynamics, phrasing, timing, articulation, texture and transitions. Each explicitly stays within requested mood, delivery, rhythm, sound sources or form. Original styles remain an unchanged prefix and lyrics are never passed through a rewrite.

A genre/negative-keyword classifier was rejected: it would miss multilingual and unconventional requests and make model prompting depend on arbitrary dictionaries. Removing Variety entirely was rejected because its existing control has a documented independent mapping. Existing recipe replay continues using saved audio and parameters.

## Risks / Trade-offs

- Less prescriptive additions may yield subtler Variety differences → retain effective prompts for inspection; do not claim audible improvements from text tests.
- ACE can still ignore explicit requests → document that preserving the supplied conditioning text is not a guarantee of music-model compliance.
- Unbounded LLM prompt expansion fails preservation gates → document pinned candidates and rejected transformations; keep the app's existing original-text behavior.

## Migration Plan

No installation/configuration/catalog migration. New generation requests use the repaired phrases, including reused drafts. Previously generated audio, original drafts and saved effective parameters are unchanged.
