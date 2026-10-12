# Design

## Context

The standalone storage helper returns detailed path lists to Python callers and prints them as a single JSON line to NSIS. A synthetic Windows reproduction using the v2.0.0 helper removes all 5,000 files and exits zero directly; `nsExec::ExecToLog` reports `error` after receiving approximately 950 KB. The three-file control succeeds through both paths.

## Goals / Non-Goals

Goals: keep the installer subprocess output small while preserving useful removed/retained counts and cleanup exit status.

Non-goals: change ownership, shared-file retention, checksums, deletion policy or recoverability of canceled downloads.

## Decisions

Only the CLI presentation changes: print counts from the existing returned lists. Detailed lists remain available to Python callers and tests. Do not suppress exceptions or ignore NSIS return codes: either would conceal real cleanup failures. Keep `ExecToLog` because the bounded summary remains useful in installer diagnostics.

Native installer tests create 5,000 synthetic owned cache fragments before the existing upgrade/default-removal test and verify that all disappear while shared/unrelated files and the library remain. Python subprocess tests cover the bounded summary and unsafe-path failure status.

## Risks / Trade-offs

An already-installed v2.0.0 uninstaller contains the old helper → a normal upgrade installs the corrected helper/uninstaller; the existing keep-models retry remains available for uninstalling an old copy.

Per-file success details disappear from the installer log → counts retain diagnostic value without risking the native logging failure or printing user paths.
