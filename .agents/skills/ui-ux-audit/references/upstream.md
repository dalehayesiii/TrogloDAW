---
name: ui-ux-audit
description: "Audit a live SaaS / product website or web app for UI/UX quality: drive Chrome to the URL at desktop + mobile viewports, screenshot every section, inject a measurement script to check contrast ratios, tap-target sizes, off-grid spacing, near-miss misalignment, animation performance, focus + reduced-motion handling, then judge visual hierarchy, flow, and consistency from the screenshots. Use whenever the user wants a website/web-app 'audited', 'reviewed for UI/UX', checked for 'misalignments' or 'anything that looks off/cheap/unpolished', or wants a design QA pass on a shipped product. Produces a prioritized blocker/major/minor report, each finding tied to a location, the violated principle, and a concrete numeric fix."
---

# /ui-ux-audit

Point it at a URL. It opens the real page in Chrome, looks at it the way a design reviewer would (desktop **and** mobile), and measures the things eyes miss — contrast in numbers, tap targets in pixels, spacing off the grid, edges that are 4px out of line. Then it judges the things numbers miss — hierarchy, crowding, whether it looks cheap. Out comes a prioritized report where every issue has a location, the rule it breaks, and a specific fix.

**Portable core:** an audit is just this playbook plus `audit.js` — a self-contained script that runs in *any* browser (through a browser-automation tool, or pasted straight into DevTools). It works on **hosted sites and local dev servers alike** (`https://…`, `http://localhost:3000`, even `file://`), so you can audit a site whether or not it's deployed.

## Usage

```
/ui-ux-audit <url>                 # full audit, desktop (1440×900) + mobile (390×844)
/ui-ux-audit <url> --desktop-only  # skip the mobile pass
/ui-ux-audit <url> --mobile-only   # mobile pass only
/ui-ux-audit <url> --full          # also add tablet (768) + record a motion GIF of one key interaction
/ui-ux-audit <url> --out <dir>     # where to save screenshots (default: /tmp/ui-ux-audit)
```

If no URL is given, ask for one. Audit whatever renders — a public marketing site, an app dashboard behind a login the user has already opened, whatever the tab shows.

## How it works

1. **Load Chrome tools** (they're deferred). One ToolSearch call:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__resize_window,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__read_console_messages`
   For `--full`, add `mcp__claude-in-chrome__gif_creator`.
2. **Measure** what's checkable (script, per viewport) → hard, numeric findings.
3. **See** what's not (screenshots, per section) → judged findings.
4. **Merge, dedupe, rank** → one report.

## Steps

1. `tabs_context_mcp` first (never reuse a tab ID from another session). Then `tabs_create_mcp` with the URL. Wait for load.
2. **For each viewport** (default desktop 1440×900, then mobile 390×844):
   - `resize_window` to the viewport, `navigate` (or reload) so responsive layout settles.
   - **Force lazy content to mount:** scroll to the bottom, then back to the top (a slow scroll pass, or run `window.scrollTo(0, document.body.scrollHeight)` via `javascript_tool`, then `0,0`).
   - **Screenshot every section** with `computer` (action: screenshot): above-the-fold first, then scroll a viewport at a time to the bottom. Save to `--out`. Name them `<viewport>-<n>.png`.
   - **Inject the measurement script:** read `audit.js` from this skill's folder and pass its full contents as the script to `javascript_tool`. It returns a JSON string — parse it. (It self-wraps every check; if a field is missing, note it, don't crash.)
   - Grab `read_console_messages` — JS errors and 404s are UX defects too.
3. **Look at the screenshots** (the `computer` result renders them; or Read the saved PNGs). Judge the vision-only rules below. Compare desktop vs mobile for the same section.
4. `--full`: use `gif_creator` to record one key interaction (open the nav menu, a modal, or a primary hover) so motion can be reviewed, not just measured.
5. **Write the report** in the format below.

## The rules

Two kinds. **Measured** rules come back as numbers from `audit.js` — report them as fact with the measured value. **Judged** rules you assess from the screenshots. Numeric thresholds below are from primary sources (cited at the bottom); don't soften them, don't invent new ones.

### Measured (from audit.js — cite the number)

| Check | Rule | Threshold | Source |
|---|---|---|---|
| Text contrast | Body/label text vs its background | **≥ 4.5:1**; large text (≥24px, or ≥18.66px bold) **≥ 3:1** | WCAG 2.2 SC 1.4.3 |
| Tap targets | Interactive elements (links, buttons, inputs) | **≥ 24×24 px** (AA min); **≥ 44×44 px** for mobile/AAA | WCAG 2.2 SC 2.5.8 / 2.5.5 |
| Spacing grid | Padding, margins, gaps | Multiples of **8** (4 tolerated for tight cases); flag off-4 values | Material 8dp grid / Android density |
| Misalignment | Sibling elements' left/right edges | Edges **1–6px** off a shared alignment line = a near-miss defect | Alignment = perceived order |
| Animation perf | Transitions/animations | Animate **only `transform`/`opacity`**; animating width/height/top/left/margin triggers layout → jank at <60fps (16.7ms budget) | web.dev, MDN |
| Easing | Non-trivial motion | Not `linear` — entering decelerates, exiting accelerates | Material M3 |
| Focus | `:focus { outline:none }` present | Must be paired with a visible `:focus-visible` style, else keyboard users are lost | WCAG 2.4.7 |
| Reduced motion | Page has motion | Should ship a `@media (prefers-reduced-motion: reduce)` block | WCAG 2.3.3 |
| Overflow | Horizontal scroll at a viewport | `scrollWidth > innerWidth` = broken responsive layout (esp. mobile) | — |
| Consistency | Distinct fonts/sizes/colors/radii/shadows in use | Flag >3 font families, >12 font sizes, >10 text colors, >6 radii, >6 shadow styles | Consistency heuristic |
| Images | Rendered vs natural size; alt attr | Displayed >1.35× natural = blurry upscale; missing `alt` = a11y gap | — |

### Motion durations (reference for checking a design system's tokens)

- Keep UI animations **100–500ms**. Simple feedback (toggle, checkbox) **~100ms**; modals/substantial changes **200–300ms**; standard mobile transition **~300ms**; **> 400ms feels slow**. Entrances slightly slower than exits. [NN/g, Material M1]
- Material M3 duration tokens: short 50/100/150/200 · medium 250/300/350/400 · long 450/500/550/600 ms.
- Material M3 easing: standard `cubic-bezier(0.2,0,0,1)` · emphasized-decelerate (enter) `cubic-bezier(0.05,0.7,0.1,1)` · emphasized-accelerate (exit) `cubic-bezier(0.3,0,0.8,0.15)`.

### Forms & errors (judge from screenshots + DOM)

- **Single-column layout** — one field per row (only short related fields like City/State/Zip may share a row). Multi-column forms are a defect. [NN/g; compliant forms ~78% first-try success vs ~42%]
- **Labels above fields**, not placeholder-only (placeholders vanish on focus). Label should sit closer to its own field than to the field above (no ambiguous equidistant spacing).
- **Errors use multiple cues** — outline **and** red text **and** icon/weight, never color alone (color-only = WCAG 1.4.1 fail). Message sits **next to the erroring field**, not only in a global banner. Bad input is **preserved**, with a specific explanation.

### Judged (from the screenshots — you decide)

- **Visual hierarchy** — can you tell in one glance what's primary? Is there one clear primary CTA per view (not three competing buttons)? First impression of polish forms in ~50ms.
- **Whitespace & crowding** — elements breathing, or jammed edge-to-edge? Grouped items read as groups (proximity), not a soup.
- **Global alignment** — do sections share a consistent content margin / grid gutter, or does each block start at a different left edge?
- **Consistency across sections** — same button styles, card styles, heading treatment, iconography throughout. Mismatched chrome reads as amateur.
- **Cheap-looking tells** — muddy gradients, harsh drop shadows, stretched/low-res images, default-blue links, clashing colors, too many fonts, stock-photo mismatch.
- **Empty / loading / error states** — compact and actionable, not a blank void or a raw stack trace.
- **Flow** — is the primary action reachable without hunting? Onboarding/first-run obvious? Nielsen heuristics as a lens: system status visibility, consistency, error prevention, recognition over recall, aesthetic minimalism. *(Canonical UX heuristics — treat as judgment guidance.)*

### Do NOT enforce (these were tested and refuted — don't invent them)

- **No fixed header:body type ratio.** A "3:1 heading-to-body size ratio" rule failed verification. Judge hierarchy by contrast/weight/space, not a magic ratio.
- **No device-scaled durations.** "Make tablet 30% slower, desktop 150–200ms" failed verification. Use the 100–500ms guidance regardless of device.
- **`internal ≤ external` spacing** (card padding ≤ gap between cards) is *guidance, not a hard check* — elements with a visible border/background may exceed it legitimately. Only flag when items lack a container and visually merge.

## Report format

Group by severity. Every finding: **location · what's wrong (principle + measured value) · fix (specific, with the number)**. Lead with a one-line verdict and the summary counts from the script.

```
# UI/UX Audit — <url>
Verdict: <one line>. Desktop + Mobile. <N> blocker · <N> major · <N> minor.

## 🔴 Blockers  (breaks usability, accessibility, or looks broken)
- Hero CTA "Get started" — text contrast 2.9:1 on the gradient (WCAG AA needs 4.5:1).
  fix: darken button bg to #1A56DB or set text #FFFFFF → yields 5.1:1.
- Mobile (390): body content overflows 34px → horizontal scroll.
  fix: the pricing table at `section.pricing > table` has a fixed 420px width; make it `max-width:100%; overflow-x:auto`.

## 🟠 Major  (looks unpolished, hurts flow)
- Feature cards misaligned: 3rd card's left edge is 5px off the shared 96px grid line.
  fix: remove the stray `margin-left:5px` on `.card:nth-child(3)`; snap to the column.
- Signup form is two columns on desktop.
  fix: single-column — one field per row (NN/g: ~78% vs 42% first-try success).

## 🟡 Minor  (nice-to-fix polish)
- Spacing uses off-grid values 13px, 27px, 5px (rest of the page is on an 8pt grid).
  fix: round to 16 / 24 / 8.
- Card hover animates `width` (triggers layout).
  fix: animate `transform: scale()` instead; keep it ~150ms, ease-out.

## Notes
- Reduced-motion: not handled (no prefers-reduced-motion block) — add one if animations are prominent.
- Console: 2 JS errors, 1 image 404 (`/hero@2x.png`).
```

### Severity rubric

- **Blocker** — AA contrast fail on primary text/CTA · tap target <24px on a primary action · broken/overflowing layout · clipped or unreadable content · focus removed with no `:focus-visible` · error state relying on color alone.
- **Major** — contrast fail on secondary text · tap targets 24–43px on mobile primary actions · visible misalignment on prominent elements · layout-triggering animation on interactive elements · multi-column form · inline errors missing · pervasive off-grid spacing.
- **Minor** — on-4-but-off-8 spacing · near-miss alignment in dense/secondary areas · `linear` easing on decorative motion · font/color/radius sprawl · missing alt · upscaled images · no reduced-motion block.

## Output contract

- **What:** screenshots under `--out` (`<viewport>-<n>.png`), plus a prioritized blocker/major/minor report where every finding names a location, the violated principle, and a concrete numeric fix.
- **End state:** report printed. If a section couldn't be reached (auth wall, interaction needed), list it as needing a manual pass. If measurement couldn't run (CSP blocks injected script), say so and fall back to a screenshot-only judged audit.

## Sources (verified, primary unless noted)

- WCAG 2.2 — https://www.w3.org/TR/WCAG22/ (contrast 1.4.3, non-text 1.4.11, target size 2.5.8/2.5.5, use-of-color 1.4.1)
- NN/g Website Forms Usability — https://www.nngroup.com/articles/web-form-design/
- NN/g Error-Message Guidelines — https://www.nngroup.com/articles/error-message-guidelines/
- NN/g Animation Duration — https://www.nngroup.com/articles/animation-duration/
- Material Design 3 motion — https://m3.material.io/styles/motion/easing-and-duration
- web.dev animation performance — https://web.dev/articles/animations-and-performance
- 8pt grid — Material 8dp / Android density buckets (secondary corroboration: designsystems.com)
