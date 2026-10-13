## Context
The UI previously derived busy state from polled jobs. During POST acceptance there is no known job, leaving action buttons enabled. Installed Edge exposed this interval; a click could coincide with the later disabled transition.

## Goals / Non-Goals
Cover API acceptance, polling and refresh with existing busy controls. Preserve editing during FX rendering and separate model-install state. Do not change queueing, cancellation, notification acknowledgement or reload behavior.

## Decisions
Use separate counters for ordinary/model submissions, increment synchronously before POST and decrement in finally after submit resolves or rejects. Existing busy bindings consume these counters. Counters tolerate overlapping callers and restore controls on errors.

The notification persistence test must wait for successful folder creation before reload. Clearing earlier errors at retry start is not completion; aborting an unfinished request correctly produces a transport error.

## Risks / Trade-offs
Controls remain busy during the final library refresh, matching completion of the user's request. Model setup remains distinct from ordinary audio operations.

## Validation
Hold an FX render POST, verify Preview remix is disabled, edit gain, release and verify stale/fresh provenance. Run notification recovery and complete browser suite including installed Windows Edge.
