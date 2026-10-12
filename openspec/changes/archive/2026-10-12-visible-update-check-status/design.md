# Design

## Context

Checks run asynchronously, while the UI polls their status. The check phase currently retains an earlier message; every failed poll is suppressed although only handoff interruptions are expected.

## Goals / Non-Goals

**Goals:** Make pending checks and transport failures observable.

**Non-Goals:** Automatically download/install or infer failures from slow authenticated release requests.

## Decisions

- Set the backend checking message before launching its worker and update manual-check UI synchronously before the POST response.
- Track a status-read error separately from the worker phase so interrupted polling does not falsely mark a live download/check as failed. A successful read replaces the state and clears that error.
- Suppress polling errors during explicit handoff or after Quit, preserving existing expected transition behavior.
- Exercise a delayed synthetic release request and an aborted status GET in the existing full browser test.

## Risks / Trade-offs

- A transient poll can fail while work continues → explain that status is unavailable and retain normal polling until recovery.

## Migration Plan

Ship through the existing PR and checks; no persisted-state migration is needed.
