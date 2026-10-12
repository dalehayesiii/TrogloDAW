# Dependency audit baseline (2026-10-11)

Python is locked through uv; Node tooling and the frontend through npm workspaces.
PostCSS is pinned/overridden to 8.5.29 after the initial audit found advisories in
the older version. Build, lint and tests verify this patch-level update.

The installed app ships compiled frontend assets and Python packages, not Node/npm
or development tools. `npm audit --omit=dev` reports no advisories for production
dependencies at this baseline. The full tooling audit still reports 14 affected
packages (12 high, 2 moderate), including parent-package cascades:

- OpenSpec/semantic-release transitively use braces/micromatch; the current braces
  release remains affected by [nested-pattern stack exhaustion](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
- semantic-release includes an unused npm publisher plugin, which brings npm
  11.21.0 and its bundled brace-expansion, HTTP cache, IP address, selector-parser
  and undici dependencies. npm cannot override/fix those bundled copies separately.

`npm audit fix --ignore-scripts` resolved the PostCSS update but cannot repair the
remaining upstream packages. Its force suggestion downgrades semantic-release to
15.x, so it is not applied. The npm publisher is excluded from our release plugins;
only GitHub assets publish. Do not describe the full audit as clean or make its
known upstream findings an unpassable required check. Revisit when upstream fixes
ship, with locked updates and the same build/test coverage.
