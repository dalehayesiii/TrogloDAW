# Spec Delta

## Purpose

Define TrogloDAW's consistent accessible purple/lavender and pale lime appearance, restrained cave identity and persistent system/light/dark preferences.

## ADDED Requirements

### Requirement: Semantic complete themes
The app SHALL provide coherent light/dark themes using purple/lavender and pale lime relationships, semantic surface/text/border/focus/status/disabled tokens and restrained cave/stone artwork. Every workflow, player, waveform, native control, overlay and job/error/empty/save state SHALL follow the active theme.

#### Scenario: Theme a picker and player
- **WHEN** appearance changes while a song picker or audio player is visible
- **THEN** surfaces, labels, native controls and waveform colors update consistently without changing audio or draft values

### Requirement: System preference and persistent choice
First use SHALL follow system appearance. Users SHALL explicitly choose light/dark and retain that override across reloads and normal app restarts on the same local origin. Returning to system preference SHALL remove the override; live system changes SHALL apply only in system mode. Initial page paint SHALL use the selected appearance.

#### Scenario: Saved dark override
- **WHEN** dark mode is selected and the browser reloads with a light system preference
- **THEN** the app remains dark with all draft/workflow values preserved

#### Scenario: Follow the system again
- **WHEN** Use system theme is chosen and system appearance changes
- **THEN** the app follows that change without overwriting an explicit override in another mode

### Requirement: Readable accessible hierarchy
Themes SHALL provide legible text, visible keyboard focus, comfortable touch targets and selected/status semantics beyond color. Requested controls SHALL remain discoverable with progressive disclosure and exactly three task-focused tabs. Representative desktop/narrow layouts SHALL avoid clipping or overlap.

#### Scenario: Navigate a narrow themed workflow
- **WHEN** a keyboard/touch user edits a clip or voice group at a narrow viewport
- **THEN** labels/actions remain readable, focus/selection is clear and all requested controls remain reachable without extra primary tabs

### Requirement: Consistent product identity
The app/header/browser title, applicable Windows installer/shortcut/uninstall metadata, current release-facing descriptions and maintained documentation SHALL identify the product as TrogloDAW. Compatibility/historical identifiers SHALL be explained rather than blindly renamed. Existing remote repository URLs SHALL remain valid.

#### Scenario: Upgrade an existing installation
- **WHEN** TrogloDAW replaces a Music Maker installation
- **THEN** displayed branding changes while existing install roots, configuration, libraries, recipes and model preferences remain usable
