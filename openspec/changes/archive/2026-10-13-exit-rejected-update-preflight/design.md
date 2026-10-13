## Context

See proposal.md. The helper's catch path attempts a recovery listener for every failure with parsed settings, including checksum rejection before handoff. With a free port it waits ten minutes instead of exiting; the native tamper test expects prompt rejection. The precise port/process condition in the failed CI runner was not captured, but the preflight listener behavior is reproducible with synthetic data.

## Goals / Non-Goals

Differentiate safe preflight rejection from recovery after service exit, while keeping verified installation/restart and retained failure diagnostics. Do not disable checksum checks, retry around the failure or change installer/update identity.

## Decisions

Track whether the validated original service has finished exiting. Set this flag immediately before taking over its status port. Before that point, write failed status and exit nonzero without opening a listener. After it, preserve the existing recovery listener behavior, including restart failure.

Run a standalone native regression with a synthetic never-executed installer and deliberately wrong hash, once with an available port and once with an occupied exclusive listener. Capture the child handle before exit and distinguish timeout, exit code and failure status in diagnostics. Invoke the fixture against the helper copied from the installed package during normal Windows handoff checks.

## Risks / Trade-offs

- Exact earlier CI port state was not captured → document the confirmed reproduction separately, preserve diagnostic output and keep all native installer checks mandatory.
- Losing post-shutdown recovery → retain existing wrong-identity/restart and stalled-shutdown end-to-end coverage.
- Preflight fixture touching personal data → use a verified temporary root, synthetic payload and only the exact child process created by the fixture; no real installer executes.

## Migration Plan

No data or configuration migration. The next ordinary CI release ships the helper fix. Existing installed versions remain usable and can install the checked release normally.
