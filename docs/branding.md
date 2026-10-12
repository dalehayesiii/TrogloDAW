# TrogloDAW product identity

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

The single release artifact is **`TrogloDAW-Setup-<version>.exe`**. SHA256SUMS contains
one matching entry and release.json identifies that filename, version, source
commit and SHA-256. Semantic-release owns version/tag decisions and versions the
already-checked frontend payload.

Current install/Documents roots, HKCU application/uninstall keys, payload paths,
launchers and project identifiers use TrogloDAW. The Python engine module is
`troglocore`, the command is `troglodaw`, environment settings use `TROGLODAW_*`,
and local API mutation requests use `X-TrogloDAW-Request: 1`. Old product-name
aliases and migration paths are not provided. Portable catalogs and recipes keep
their audio contracts; configured model/library locations remain user choices.

The existing **dalehayesiii/music-maker** GitHub remote and links remain real
repository addresses; renaming that remote requires the owner. Archived OpenSpec
changes and Git history retain truthful historical names and screenshot evidence. Generated
workflow instructions remain upstream material rather than product branding.

Current TrogloDAW upgrades preserve configuration and models. Installation and
uninstall manage only known app shortcuts and preserve unrelated custom Start
Menu entries. Model removal is ownership-aware and checked by default with
opt-out; libraries are preserved.

Generation shows original input clips. Content-aware sampling derives smaller
samples, transforms each individually and arranges one complete audio guide.
Sample management is automatic. The result area has a fixed **Song generation
output** heading with the actual song title below it.

Theme checks use axe-core against the real backend, plus system/override/reload,
canvas-repaint and narrow-layout tests. Current dark-mode app screenshots appear
in the [repository overview](../README.md); before/after review evidence belongs
to the relevant pull request.

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
cover Generation, Library, Vocal FX, setup and key error/dialog states.
