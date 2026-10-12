# Installation and data recovery

## Update an existing installation

Use **Settings → App updates**, or run the newer installer against the same installation directory. Preferences, library/models and setup history are retained. Initial setup does not repeat merely because the version changed or a model download was deferred/interrupted. You can resume model verification/installation through Settings. Close the setup dialog with **Continue in background** after installation starts; keep the TrogloDAW service running. Download and Installation are separate scopes: complete model-file bytes still require verification and runtime preparation.

## Reinstall while retaining data

Uninstall removes the app and its preferences. Model removal is checked by default; uncheck it to retain model assets. Your library remains on disk. A fresh installation therefore opens first-run setup again, even if old folders exist.

1. Select your retained **Library folder** and **Model storage folder** in first-run setup using the directory pickers.
2. Choose **Use folder without moving** when prompted if the selected destination already contains the data you want to reuse. Choose **Move existing data** only when transferring the currently active data to an empty destination.
3. Choose the matching supported model and click **Install / verify selected model**. Complete pinned assets and compatible runtime files are verified and reused; only missing files are downloaded. Incompatible existing files are preserved and reported rather than overwritten. Interrupted partials owned by a previous installation may remain; they are not silently adopted as verified model files.

Selecting a folder does not itself start a download. Setup can be deferred; importing, recording, browsing, playback and draft editing work without a music model. New song generation and fresh source extraction need a ready compatible model. Existing cached edits may remain usable.

## Data inside app program folders

Keep user libraries/models outside the installed `app` and `python` directories; upgrades replace those directories. New selections reject those locations. If an older installation has data there, uninstall stops before deleting it. Open **Settings**, select an empty safe folder, and choose **Move existing data**. The app copies and verifies managed data before switching preferences and removes only safe originals; shared, changed or unrelated files remain. Preserve any remaining unrelated files yourself before removing the app.

Relocate unsafe legacy storage before running a newer installer manually. In-app update handoff checks these locations and refuses unsafe upgrades; a manual installer cannot recover data placed inside program directories that it replaces.

An empty historical storage folder containing only ownership metadata does not block uninstall after a completed move. A historical reserved folder still containing assets remains a recovery concern and is preserved.

## Uninstall after canceled setup on 2.0.0

Version 2.0.0's uninstaller can falsely report failure after successfully cleaning thousands of setup cache files because its output is too large. Upgrade to a fixed release before uninstalling, or retry that older uninstaller with model removal unchecked. Later releases use a bounded removal/retention summary. Actual unsafe metadata or filesystem failures still report failure; do not discard retained data to work around them.

## Future compatibility changes

Installation/configuration compatibility changes must ship with a guide under `docs/` and a README link describing affected versions, preservation, migration, verification and recovery. The current update does not require relocating normal external libraries/models or redownloading compatible assets.
