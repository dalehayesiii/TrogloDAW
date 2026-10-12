# Design

## Context

The private `dalehayesiii/music-maker` repository already publishes one canonical Windows installer plus SHA256SUMS and release.json. NSIS upgrades preserve config and chosen asset locations. The app currently lacks an embedded release identity and installer handoff. See proposal.md for the authorized network exception; audio/inference stays local.

## Goals / Non-Goals

Goals: asynchronous stable-release checks, explicit verified download and idle-only Windows upgrade, including private releases and paths with spaces.

Non-goals: remote audio processing, unattended installation, repository rename, release version planning, prerequisite Node/gh installation or browser closure.

## Decisions

- A dedicated update manager/thread handles metadata/transfers separately from the sequential DSP worker. The compiled UI polls public status, presents an available-version notice and keeps detailed controls in Settings. Source/development builds do not attempt installed-app upgrades.
- Read the packaged version/source identity created by the existing semantic-release prepare hook. Compare stable SemVer tuples with GitHub's latest published stable release; never calculate a new release version. The package's version/source and final service health are checked in release smoke.
- Use stdlib HTTPS with bounded metadata, timeouts and approved GitHub hosts. Authentication can use an optional Windows generic credential, explicit environment token or existing CLI token (preferred account first). A redirect handler strips credentials when hosts change. Private access is optional and never shipped. GitHub's [release API](https://docs.github.com/en/rest/releases/releases) requires repository Contents read for private releases; its [asset endpoint](https://docs.github.com/en/rest/releases/assets) can redirect downloads.
- Download only the canonical uploaded asset into an installation-owned update directory in selected model storage. Cross-check the release tag, manifest version/source/filename, checksum entry, API asset length and downloaded SHA-256. Cancellation clears readiness; failures retain the current app.
- Serialize handoff with service job admission, upload accounting and native picker state. Browser recording leases renew while microphone access/recording is active; all unexpired leases gate installation. A stale closed-tab lease expires conservatively.
- Copy the PowerShell helper and a credential-free plan outside the installed app. It validates/acknowledges its plan, waits for the backend PID to exit, checks the installer hash again, runs NSIS silently against the existing install directory, verifies the resulting version and restarts only after success. The backend stops only after helper acknowledgment. A durable status/log and verified installer support retry after an installation failure.

## Risks / Trade-offs

- Unsigned installer → retain existing distribution behavior and require matching trusted release metadata/checksum; no claim of code signing.
- Private repository without credentials → quiet recoverable status and Settings access guidance, without compromising offline audio.
- Interruption during NSIS execution → do not claim automatic binary rollback; preserve user data and the verified installer/status for recovery. Before handoff, download/launch failures leave the current app running.
- A crashed recording tab leaves a lease → wait for expiry before installation, preserving active recording rather than force-stopping it.

## Migration Plan

Ship through the normal PR/semantic-release pipeline. Future installed builds carry version identity; source builds remain explicit. Existing library/model preferences and owned assets need no migration. Disabling startup checks removes automatic metadata requests; updates remain explicit.
