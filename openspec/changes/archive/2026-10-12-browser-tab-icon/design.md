## Context

The existing header logo is inline SVG; Angular already copies public assets and Windows packaging copies the complete compiled UI.

## Decisions

Use the same vector paths with fixed purple/pink, dark cave and pale lime colors in a standalone SVG. A transparent outer canvas and dark cave retain contrast on light and dark browser chrome. Declare `rel=icon`, `type=image/svg+xml` and `sizes=any` in index.html. No generated image, new toolchain, external asset request or runtime dependency is required.

## Validation

Build the actual UI, inspect its icon declaration and response against the real backend, and render the icon at 16/32 pixels on light/dark surfaces. Run documented checks and retain native installed verification in required Actions. Sync and archive the complete change before the separate PR.
