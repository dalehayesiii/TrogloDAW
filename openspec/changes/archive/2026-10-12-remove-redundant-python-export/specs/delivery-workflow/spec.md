# Spec Delta

## ADDED Requirements

### Requirement: Single Python dependency source
Python dependency declarations SHALL live in pyproject.toml and resolved versions
in uv.lock. Source setup SHALL use the locked environment. Windows builds SHALL
generate temporary hashed runtime requirements from that lock and install only
compatible Windows wheels with hash verification. No requirements.txt export SHALL
be tracked at the repository root or included in the installed app.

#### Scenario: Build without a tracked export
- **WHEN** a preview Windows installer is built from a clean checkout
- **THEN** dependency installation succeeds using a fresh temporary lock export
  and the installed app runs without a shipped requirements.txt

#### Scenario: Dependency maintenance
- **WHEN** a developer updates a Python dependency
- **THEN** pyproject.toml and uv.lock are the maintained dependency files and no
  separately maintained compatibility export is required
