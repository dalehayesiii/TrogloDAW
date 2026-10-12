# Design

## Context

The app is a local browser UI backed by Python. Browser-tab closure does not terminate Python. Existing reuse probes only port 7860 and does not serialize launch attempts. GitHub releases are private and the desktop process can inherit a PATH older than a later CLI installation.

## Goals / Non-Goals

**Goals:** Reliable reopen without duplicate services and useful automatic/manual release access.

**Non-Goals:** Read browser cookies, change repository visibility, automatically install updates or stop active work on tab closure.

## Decisions

- Keep a nonblocking OS file lock for the configuration root for the service lifetime. Separate ephemeral metadata identifies its URL and random launch ID. Reopen verifies that ID through health; stale metadata alone cannot suppress a fresh start or identify an unrelated listener.
- Serialize port selection and reserve a listening socket before running Uvicorn. Default-port collisions choose an available local port. Duplicate startup waits for verified readiness or the first process's lock release, with a bounded timeout and no extra service.
- Keep browser closure independent of service lifetime; Quit uses graceful server shutdown so background resources and launch ownership release together.
- Find CLI through PATH, then standard Windows installation locations, and try preferred usernames followed by active CLI access. Keep all tokens in memory and deduplicate them.
- Offer a fixed HTTPS latest-release link in Settings. That browser navigation uses the browser's login for manual download; backend verified automation continues to use separate credentials.

## Risks / Trade-offs

- Crashed service leaves metadata → OS lock releases automatically; a new owner overwrites stale metadata.
- Existing older launchers lack the new health identity → avoid trusting unrelated service responses; document Quit before the first upgrade.
- Slow startup → duplicate launch waits for readiness and reports a recoverable timeout instead of creating a second process.
- Browser-only access cannot drive backend verification → describe manual browser access distinctly from verified in-app downloads.

## Migration Plan

Deliver with the existing installer filename change. Quit the previous app before the one-time manual upgrade. Configuration, model/library paths and recipes remain compatible; new launch state is ephemeral.
