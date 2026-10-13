## ADDED Requirements

### Requirement: Stable installed shortcuts
Same-directory Windows updates and reinstalls SHALL reuse existing known app shortcuts without rewriting their files, preserving user placement and customization. Missing shortcuts SHALL be created. Installing into a different directory SHALL refresh targets. Uninstall SHALL continue removing the known app shortcuts while preserving unrelated entries.

#### Scenario: Reinstall in the existing folder
- **WHEN** a registered installation is reinstalled in the same directory with existing desktop and Start Menu shortcuts
- **THEN** those shortcut files retain their contents and creation/write times

#### Scenario: Upgrade through the app
- **WHEN** the verified update helper installs a new version into the existing directory
- **THEN** existing app shortcut files remain unchanged

#### Scenario: Missing shortcut
- **WHEN** a fresh install or same-directory reinstall has a missing known shortcut
- **THEN** that shortcut is created with the current application target

#### Scenario: Changed installation directory
- **WHEN** installation uses a different directory from the registered previous installation
- **THEN** known shortcuts target the new directory
