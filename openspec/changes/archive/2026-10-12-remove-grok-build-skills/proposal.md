# Proposal

## Why

The committed `.grok/skills/` copies duplicate `.agents/skills/` except for slash-command
syntax. The hosted TrogloDAW Grok bot has no slash commands, does not auto-load repo
skills and works from a separate Linux box, so it needs plain instructions instead.

## What Changes

- Delete `.grok/` and drop `grok` from the documented `openspec init --tools` refresh.
- Remove Grok Build from the development guide's tool table.
- Add a short AGENTS.md section for agents without slash-command support: read the
  `.agents/skills/openspec-*` SKILL.md files directly, start from latest origin/main,
  and verify `gh auth status` and permissions off Steve's computer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `delivery-workflow`: Supported OpenSpec workflows no longer include Grok Build;
  agents without slash commands follow the canonical skill files manually.

## Impact

`.grok/`, AGENTS.md, docs/development.md and the delivery-workflow spec. App code,
CI, `.agents/` and `.gemini/` are unchanged.
