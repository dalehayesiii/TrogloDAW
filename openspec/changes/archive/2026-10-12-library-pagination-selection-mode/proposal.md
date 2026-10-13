## Why

Long Library lists need bounded pages. Always-visible checkboxes crowd ordinary browsing and do not communicate selection scope clearly.

## What Changes

- Paginate filtered songs with 20 by default and 10/20/50 choices, range and previous/next controls.
- Reveal checkboxes and batch tools only after Select songs; Done selecting clears and hides them.
- Restrict selection to the current page; clear on page/filter/size changes and reconcile refreshes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `frontend-service`: page-scoped opt-in Library selection and pagination.

## Impact

Angular list presentation, browser regressions and Library help. Catalog/API/storage contracts remain compatible.
