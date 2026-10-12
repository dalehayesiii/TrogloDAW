# user-interfaces Specification

## Purpose

Describe TrogloDAW's browser workflows and compatible command-line interface for local music creation, organization and voice editing.

## Requirements

### Requirement: Browser interface
The Angular interface SHALL expose Generation, Library and Vocal FX with persistent drafts and direct cross-tab song actions. It SHALL launch on configured localhost/default free port, open a browser unless suppressed and provide a quit action. Library uploads, accepted recordings and playback SHALL use local managed files. Storage/model settings SHALL use a compact dialog/drawer.

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

### Requirement: One running browser app per configuration
The launcher SHALL maintain one running service per configuration root, reopening its verified local URL on later desktop launches even when it uses a nondefault port. Concurrent launch attempts SHALL not create duplicate services. Closing a browser tab SHALL leave background work running; Quit SHALL stop the service. Crashed services and stale launch state SHALL permit a fresh launch, without treating unrelated listeners as this app.

#### Scenario: Close and reopen
- **WHEN** the user closes the tab and launches the desktop shortcut again
- **THEN** the existing service is reused and its browser UI reopens without another background service

#### Scenario: Default port occupied
- **WHEN** another application owns the default port
- **THEN** TrogloDAW chooses an available local port and subsequent launches reuse that instance

#### Scenario: Concurrent launches
- **WHEN** two launches start together for the same configuration
- **THEN** one starts the service and the other waits for verified readiness without starting another service

#### Scenario: Restart after exit
- **WHEN** Quit finishes or the service crashes leaving stale launch metadata
- **THEN** the next launch can start a fresh service
