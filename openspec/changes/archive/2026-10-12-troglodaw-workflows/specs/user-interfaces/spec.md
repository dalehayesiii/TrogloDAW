# Spec Delta

## MODIFIED Requirements

### Requirement: Browser interface
The Angular interface SHALL expose Generation, Library and Vocal FX with persistent drafts and direct cross-tab song actions. It SHALL launch on configured localhost/default free port, open a browser unless suppressed and provide a quit action. Library uploads, accepted recordings and playback SHALL use local managed files. Storage/model settings SHALL use a compact dialog/drawer.

#### Scenario: Source launch
- **WHEN** backend/app.py launches with --no-browser
- **THEN** it serves the UI without opening a browser automatically
