# user-interfaces Specification

## Purpose
Describe the initial browser and command-line interfaces exposing the same offline music library and engine.

## Requirements

### Requirement: Browser interface
The Angular interface SHALL preserve the initial Gradio layout and expose Library,
Voice FX, Generator, Mixer/Remix and
AI Producer operations. It SHALL launch on configured localhost/default free port,
open a browser unless suppressed and provide a quit action. Library uploads and
playback SHALL use local managed files.

#### Scenario: Source launch
- **WHEN** backend/app.py launches with --no-browser
- **THEN** it serves the UI without opening a browser automatically

### Requirement: CLI interface
The CLI SHALL expose library import/list/show/tag/rename/delete, voice-fx,
generate, mix/remix/rerender/export, analyze/produce, tts, where and demo commands.
It SHALL invoke the same core functions and accept ids, prefixes or names.
Existing Windows/macOS/Linux launchers SHALL remain available.

#### Scenario: End-to-end demo
- **WHEN** backend/cli.py demo runs against a temporary library
- **THEN** it creates a test voice, processed voice, generated beat, mix and remix
  and exports playable files without a remote API
