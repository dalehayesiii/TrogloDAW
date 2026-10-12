# TrogloDAW branding and compatibility

TrogloDAW is the current product name in the app/header/browser title, Windows
installer/product/uninstall metadata and shortcuts, startup/console messages,
README and maintained product/development/packaging guides. The cave-arch waveform
mark uses pink-purple/lavender and pale lime; a cave-wall contour and mammoth mural,
carved workflow glyphs, stone strata and rhythm marks extend the identity across
task panels. Purple-family accents predominate; deliberate lime player, waveform,
selection and setup accents provide approximately a quarter of the accent design.
Semantic tokens tune text/control colors
for readable light/dark themes. System appearance applies on first paint, explicit
choices persist in browser local storage, and Settings can return to system mode.
Browser preferences are scoped to the normal local origin; separate ports have
independent storage. No external fonts/artwork or Node runtime are required.

The canonical release artifact is **TrogloDAW-Setup.exe**. A byte-identical
**MusicMaker-Setup.exe** alias supports existing download automation. SHA256SUMS
lists both, release.json identifies the canonical name, and the publisher verifies
the aliases against its tested version/source/checksum. Semantic-release owns all
version/tag decisions and versions the already-checked frontend payload.

These names intentionally remain:

| Identifier | Reason |
| --- | --- |
| dalehayesiii/music-maker and existing GitHub URLs | The owner will rename the remote later; this change preserves real links |
| MusicMaker install/Documents roots and HKCU application/uninstall key | Existing installs, model/library preferences and upgrades keep resolving |
| mm / MM_* / config filenames / mmcore | Existing CLI, environment, configuration and recipe automation contracts |
| MusicMaker.vbs, Music Maker (console).bat and musicmaker.ico payload paths | Compatible internal launcher/icon names; displayed titles and shortcuts say TrogloDAW |
| Python project musicmaker, npm tooling/Angular project identifiers, local request header and health application field | Internal build/API compatibility; health also exposes product=TrogloDAW |
| Existing temporary-test prefixes | Isolated implementation details, not product UI |
| Archived OpenSpec changes and Gradio/initial migration screenshots | Historical evidence is not rewritten |

Upgrade migration removes only known old Music Maker shortcuts. Custom entries
stay; new shortcuts identify TrogloDAW. Uninstall removes known app shortcuts and
leaves unrelated custom entries. Model removal remains ownership-aware and checked
by default with opt-out. Libraries and existing installed roots are preserved.

Audit: search maintained frontend/backend, scripts, cicd, config, README, docs and
canonical specs for musicmaker/Music Maker/MusicMaker/Degenerate Music Creator.
The remaining matches above are deliberate compatibility/history references.
Theme checks use axe-core against the real backend, plus system/override/reload,
canvas-repaint and narrow-layout tests. Paired review evidence is under
[themes](ui-parity/themes/README.md).

Measured semantic contrast (actual hex tokens, WCAG luminance calculation):

| Role | Light | Dark |
| --- | --- | --- |
| Text | 13.91:1 | 12.75:1 |
| Secondary text | 5.79:1 | 7.14:1 |
| Primary button | 6.44:1 | 7.27:1 |
| Error | 6.89:1 | 8.98:1 |
| Warning | 6.70:1 | 8.93:1 |
| Disabled text | 5.24:1 | 5.95:1 |
| Control boundary | 3.74:1 | 3.26:1 |
| Control boundary on inset | 3.46:1 | 3.58:1 |
| Lime accent text | 7.27:1 | 8.05:1 |
| Header secondary text | 7.25:1 | 7.16:1 |

Text pairs exceed 4.5:1; control boundaries/focus exceed 3:1. Automated axe checks
cover the rendered states listed in the screenshot guide.
