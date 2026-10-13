# Design

## Context

See proposal.md. The updater currently tries specific usernames before the active CLI identity. The agent's installation-wide preferences are separate from product behavior.

## Goals / Non-Goals

**Goals:** Remove personal identity assumptions from tracked files and use the user's active CLI credentials.

**Non-Goals:** Modify installation-wide instructions, switch authentication accounts, alter credential storage, rewrite Git history or change update verification.

## Decisions

- Invoke GitHub CLI once without a username. Enumerating all authenticated users was considered but would still silently choose identities the user did not select.
- Keep credential precedence and token deduplication: saved credential, explicit environment token, active CLI credential, public access. Authentication failures retain the existing quiet recovery behavior.
- Update tests with synthetic credential-source labels; leave no personal usernames in fixtures or new artifacts.

## Risks / Trade-offs

- An active CLI identity without release access no longer benefits from a hidden alternate-account fallback → the user can select the intended CLI identity or supply release access explicitly.

## Migration Plan

Existing saved credentials and configuration remain valid. No migration is required.
