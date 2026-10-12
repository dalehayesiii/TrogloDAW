# App updates

Installed Windows builds check the latest stable GitHub release in the background on startup. Audio, lyrics, generation and your library remain local. Release checks send no song data. Offline access failures do not prevent normal use.

Open **Settings → App updates** to check manually or turn startup checks off. An available-version notice opens these controls. **Download** is explicit and shows actual bytes and a transfer estimate; you can cancel and retry. The app verifies the canonical installer against its release manifest, checksum, source tag and asset size before offering **Install update and restart**.

Installation waits for processing, uploads, folder selection and recording in every app tab to finish. The update helper acknowledges its plan before TrogloDAW stops, runs the verified installer against the existing installation, and restarts the app on the same localhost port. A status page replaces the controls during installation; it returns to the app after restart. Models, library folders and installation preferences—including completed or deferred initial setup—are reused.

## Private release access

This repository currently has private releases. The app can reuse an existing GitHub CLI login (purpledragondude7 first, then s116821), an explicit `TROGLODAW_GITHUB_TOKEN`, or a token you save through **Private release access**. GitHub CLI is optional. A fine-grained token needs read access to repository **Contents**. Save tokens only through the password field; they are stored in Windows Credential Manager for this installation, never in JSON preferences or song recipes. Uninstall removes this installation's saved access even when models are retained. Credentials are stripped from redirects to other approved download hosts.

## Recovery and limitations

Download, verification or helper launch failures leave the current app running. Retry the operation after resolving connection, disk-space or access issues. Downloads/helpers use the selected model drive; a controlled sibling cache is used if that location is inside the installation directory.

If native installation fails after handoff, the status page identifies the verified installer retained on disk. Run it to repair the same installation or reopen TrogloDAW from its shortcut when its files remain usable. Binary rollback is not automatic. Keep your existing library/model folders; see [installation and data recovery](installation-recovery.md).

Source/development builds and unsupported platforms show their status explicitly and do not run installed Windows upgrades. Prereleases are excluded. The installer follows the repository's existing unsigned distribution policy; checksum/source verification does not claim code signing.
