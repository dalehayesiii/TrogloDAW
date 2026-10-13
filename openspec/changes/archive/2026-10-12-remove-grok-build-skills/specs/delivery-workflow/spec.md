# Spec Delta

## MODIFIED Requirements

### Requirement: Full OpenSpec lifecycle and agent support
The repo SHALL provide pinned OpenSpec CLI/workflows for Codex, Gemini CLI and
Antigravity; agents without them SHALL follow `.agents/skills/openspec-*` manually.
Changes warranting specs SHALL normally include
proposal, design, tasks, implementation, canonical spec sync and archive in one PR.
Proposal-only exceptions SHALL require explicit user intent, a docs PR and the
openspec:proposal-only label. CI SHALL reject unfinished archived tasks and
unapproved active changes.

#### Scenario: Normal implementation
- **WHEN** an agent finishes a behavior or delivery change
- **THEN** its PR contains completed archived artifacts and updated canonical specs

#### Scenario: Agent without slash commands
- **WHEN** an agent cannot run OpenSpec slash commands or auto-load skills
- **THEN** it follows the canonical `.agents/skills/openspec-*` instructions by hand
