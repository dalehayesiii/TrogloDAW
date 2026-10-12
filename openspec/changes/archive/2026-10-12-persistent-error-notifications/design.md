# Design

## Context

See proposal.md. The app stores every backend job in memory and renders all failed/canceled jobs. Polling throws terminal failure text, then action handlers also render a global error. General errors have no origin or dismissal. Success messages already expire after eight seconds.

## Goals / Non-Goals

Preserve every outstanding failure until acknowledgment or its relevant retry, including across reload. Preserve job/result/timing APIs. Do not add a backend history database, a fourth tab, dependencies or generation behavior.

## Decisions

- A small frontend notification ledger stores acknowledged job IDs and scoped ordinary errors in localStorage. Prune acknowledgments only against a successful full backend job snapshot; active jobs always override dismissal.
- Derive scope from job action automatically: generation, lyrics, Vocal FX (prepare/render), model setup, storage, input audio; other actions retain their own action scope. Direct operations explicitly tag their originating scope. This lets future lyrics_generate jobs work without special caller cleanup.
- Starting an attempt acknowledges existing terminal jobs/errors in that scope. It does not acknowledge active jobs or unrelated workflows. Terminal job failure throws a represented-error marker so caller error handlers do not duplicate it; network/submission errors remain ordinary scoped errors.
- Render active jobs plus the newest terminal notice per scope, with an earlier-notices disclosure. This retains old outcomes without an unbounded expanded stack. Dismissal affects presentation only.
- Use one notification template in the foreground page/dialog. New errors use alert semantics, active/canceled updates use polite status; restored errors have no live role. Success expiry and historical-silent restoration remain unchanged.

## Risks / Trade-offs

- Browser storage unavailable → current-session dismissal works, with documented persistence limitation.
- Concurrent background work → acknowledgments only cover already-terminal jobs, never active/future outcomes.
- Root lyric planning change also touches app.ts → keep action scoping centralized and new module isolated for straightforward integration.

## Migration Plan

Existing jobs remain in the backend; first load groups their unacknowledged errors without deleting any. New localStorage data is versioned and validated; corrupt data is ignored. Rolling back ignores the new presentation key.
