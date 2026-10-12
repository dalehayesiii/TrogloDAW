# Design

## Context

The existing same-origin shutdown endpoint acknowledges the request before exiting. Angular currently updates only a status line and leaves every workflow visible. The Quit button already prevents shutdown during an active operation.

## Goals / Non-Goals

Goals: make acknowledged completion obvious, accessible and independent of a running backend.

Non-goals: automatic browser closure or changes to backend shutdown/job cancellation.

## Decisions

Use a terminal Angular state that replaces the root view after the existing API call succeeds. Inline the established cave logo so the confirmation needs no asset request after service exit. Stop local media, close the dialog and focus the confirmation heading after rendering. Disable duplicate pending Quit requests. Keep the existing interface on request failure and clear pending state to allow retry.

## Risks / Trade-offs

The service exits shortly after acknowledgment → render the static completion page immediately and avoid further service requests.

Browser-created tabs usually cannot close themselves → explicitly tell users to close the window, without relying on `window.close()`.
