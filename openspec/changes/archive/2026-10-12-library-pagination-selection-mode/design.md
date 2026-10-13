## Context

The service supplies the complete catalog for audio/reference pickers. Paginate its filtered song view locally without changing these consumers.

## Goals / Non-Goals

Bound visible rows and disclose selection intentionally. Preserve independent playback and existing confirmations/partial retry. No backend pagination, sorting change or catalog migration.

## Decisions

Use 20 rows by default, with 10/20/50 choices and bottom range/page navigation. Follow Carbon's pagination anatomy and contextual batch toolbar; explicit Select songs is the requested adaptation rather than Carbon's always-selectable table variant. Keep selection to the current page and clear it on page/filter/size changes or Done selecting. Refresh clamps to the last valid page and prunes hidden/missing IDs. A selected preview can remain across pages. Mode survives tab navigation but starts off on reload.

Sources: https://www.carbondesignsystem.com/building-blocks/core/components/pagination/guidelines and https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines.

## Risks / Trade-offs

This bounds rendering, not catalog transfer. Cross-page bulk selection is intentionally unavailable; visible names/counts match confirmation. Active processing disables page navigation and selection actions. Partial failures retain visible unsuccessful selections.

## Validation

Real-service synthetic multi-page tests cover browsing, search/folder resets, size changes, selection mode, visible-page-only mutation and last-page deletion. Review desktop/narrow in both themes and retain existing failure/retry coverage.
