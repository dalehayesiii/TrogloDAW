# Design

## Context

WRK-4 supplies three task-focused workflows, progressive settings, local setup and portable audio assets. This change uses the attached 108x108 purple/lavender and pale lime reference, preserving field meanings and runtime identifiers. The GitHub repository remains dalehayesiii/music-maker until its owner renames it.

## Goals / Non-Goals

Goals: clearly brand TrogloDAW, improve hierarchy/contrast, consistently theme all controls/players/dialogs, persist appearance and maintain installed/release compatibility.

Non-goals: new model/audio behavior, additional generation controls, calibrated ETAs, updater implementation, remote repository rename or restyling historical archive evidence.

## Decisions

1. Use semantic CSS tokens for page/surface/elevation, text/muted text, brand/on-brand, lime accent, border/focus/selection, success/warning/error, disabled and waveform states. Keep legacy token aliases internally while removing hardcoded widget colors. Use darker plum text/button derivatives in light mode and brighter lavender on dark surfaces; measure actual contrast pairs. A small cave-arch/waveform mark and subtle stone geometry provide the motif without decorative noise.
2. Read a valid local appearance override before first paint; otherwise follow matchMedia. Persist explicit light/dark overrides in browser local storage, provide Use system theme, and follow live system changes only in system mode. Apply native color-scheme and repaint canvas waveforms on theme changes. Normal local browser origin survives app restarts; no Node runtime or remote assets are introduced.
3. Preserve the three workflows and collapsed options. Improve spacing, keyboard focus, touch targets, selected-item semantics and compact result downloads. Keep creation inspection, sample/FX details and model setup disclosed on demand. Product labels remain plain despite the cave artwork.
4. Keep MusicMaker installed roots, registry key, mm commands, MM_* environment/config contracts and internal launch aliases. Display TrogloDAW in browser/app/installer/shortcuts/uninstall metadata. Remove only known old shortcuts when replacing branding; preserve custom entries. Publish TrogloDAW-Setup.exe as canonical and retain byte-identical MusicMaker-Setup.exe for existing automation. Checksum/publication guard validates both against the same semantic-release version/source. Never compute a release version or rebuild checked frontend assets.
5. Update maintained prose and canonical capability descriptions; leave archived changes and old parity screenshots historical. Document intentional old identifiers and real repository URLs in a branding audit. Paired theme screenshots use synthetic libraries; functional tests exercise real backend and installed runtime.

## Risks / Trade-offs

- Sampled reference colors are decorative starting points; direct text use may fail contrast. Tune semantic derivatives and measure them.
- Canvas/native widgets can retain old colors. Tokenize controls, use color-scheme and test waveform repaint plus key overlays in both themes.
- Renaming artifacts/shortcuts can break automation or upgrades. Keep explicit aliases/old install keys and test installed metadata, shortcut migration and matching hashes.
- Browser local storage is tied to origin. Normal app restarts retain the configured local origin; separate concurrent instances/ports have independent browser preferences.
