## Context
Observed update status reported The running app did not stop; the original pythonw process had no listener but retained the instance lock. A read-only stack dump showed Uvicorn's event loop awaiting shutdown, with idle DSP/setup workers. The helper only created its listener after process exit and did not check whether its restarted app became healthy.

## Goals / Non-Goals
Finish acknowledged idle updates despite stalled HTTP teardown. Preserve configured data, verified artifacts, identity checks and busy gates. Keep graceful worker cleanup for ordinary Quit. Do not change generation, update authentication, installer identity or release versions.

## Decisions
Configure ten-second graceful HTTP teardown so disconnected/stalled requests cannot block lifespan cleanup indefinitely. The updater still waits thirty seconds; if necessary, it checks the exact original executable/start time again and terminates only that reserved idle process, then waits for exit. Reused PIDs or changed paths are never terminated.

Keep a status listener for failures when the original port becomes available, including pre-install failure. After install, close the listener, launch with diagnostic logs and verify application/version/source/frontend health within sixty seconds. Failed restart reopens recovery status when possible. Browser unavailable status becomes an actionable warning after forty-five seconds, while polling continues and clears the warning on successful status reads.

## Risks / Trade-offs
The fallback forcibly exits an already acknowledged idle app; it is never used for active audio work or unrelated processes. A foreign listener can prevent serving recovery status; the browser warning and retained status/log/artifacts still provide recovery. Restart logs are local and must not include credentials.

## Validation
Synthetic hung ASGI request proves the launcher exits and releases its lock. Native isolated installation exercises timeout fallback and confirmed restart, tamper rejection, identity failure and restart diagnostics. Browser tests cover unavailable/returned handoff status and recovery layout.
