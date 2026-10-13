## Context

`openspec init --tools ...` generates per-tool skills; only the documented refresh
command lists `grok`. No CI, script or ignore rule references `.grok/`.

## Decisions

Remove `grok` from the refresh command so OpenSpec will not regenerate `.grok/`.
Keep `.agents/skills/` as the canonical skills for agents lacking a native loader.
Add the guidance to AGENTS.md without changing the Steve's-computer bullet.

## Validation

Search for remaining `.grok` references, run strict change and spec validation, and
monitor required Actions on the PR.
