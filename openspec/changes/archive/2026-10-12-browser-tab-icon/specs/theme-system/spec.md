## ADDED Requirements

### Requirement: Recognizable local browser-tab icon
The browser document SHALL declare a locally served TrogloDAW cave-logo favicon. The same recognizable purple/pink stone, dark cave and lime waveform SHALL remain visible on light and dark browser chrome in supported browsers, including the packaged app, without an external asset request.

#### Scenario: Identify the app tab
- **WHEN** the source or installed app opens in a supported browser
- **THEN** the browser document references the bundled logo favicon and its asset is served locally with the SVG image content type
