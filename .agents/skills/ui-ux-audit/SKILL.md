---
name: ui-ux-audit
description: Review TrogloDAW frontend usability when auditing UI/UX or changing frontend interaction, layout, controls or visible feedback. Apply proportionately to the affected flow; backend-only, docs-only and test-only maintenance do not need a full browser audit.
---

# TrogloDAW frontend usability

Read [the vendored audit playbook](references/upstream.md) for reusable measurement
and screenshot guidance. This entrypoint adapts it to this repository; the
instructions below take precedence over upstream tool assumptions and heuristics.

- Prioritize everyday usability: truthful audio/selection state, understandable
  actions, loading and failure recovery, preserved drafts, empty states and
  practical mouse/touch controls. The user does not want broad accessibility
  compliance work; preserve established tests and address accessibility overlaps
  when they also affect ordinary interaction.
- Keep the existing three workflows and progressive disclosure. A visual redesign
  needs its own requested scope. Follow root AGENTS.md and OpenSpec for delivery.
- Review the changed flow in the compiled app with synthetic audio and a temporary
  library using the existing Playwright setup. For layout changes inspect desktop
  (1440px) and narrow (390px) screenshots in both themes. For interaction changes,
  exercise loading, success, failure/retry and stale asynchronous responses where
  relevant. Do not run unrelated full audits for minor repairs.
- Use available Playwright/browser tools; Claude-in-Chrome is not required. Run
  `scripts/ui-ux-audit.js` inside the page with `page.evaluate(scriptText)` when
  measurements help. It returns a JSON string. Read the script before injection;
  no download, plugin install or remote execution is required.
- Treat its numbers as leads. Label-associated checkboxes, hidden dialogs,
  decorative artwork, disabled controls and browser rounding can cause false
  positives. Spacing-grid/font-count heuristics are not product requirements.
  Confirm a usability problem in a screenshot or interaction before fixing it.
- Give each confirmed finding a location, severity, user consequence and concrete
  repair. Report findings during work so the user can steer. Keep an audit record
  or PR summary of fixes, verification and unresolved limitations.
- Add regression coverage for meaningful behavior changes to the existing frontend
  unit/real-service E2E tests. The established Windows installed-app job runs E2E;
  no additional CI workflow or generic design score is needed.

Upstream: `imYChaudhary22/ui-ux-audit` commit
`9db3658b157e4e014f8071810cff6514ab73848a` (MIT). `references/upstream.md`,
`scripts/ui-ux-audit.js` and `LICENSE` are unmodified source files. See
[audit provenance and review limits](../../../docs/frontend-ux-audit.md) for details.
