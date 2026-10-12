## MODIFIED Requirements

### Requirement: Selected model destination
Settings SHALL show and persist a separate model-storage folder. Initial setup and Settings SHALL offer a user-triggered native Windows directory picker rather than requiring typed paths. Before every new model download, users SHALL see/change its destination, role, compatible hardware and known size. All required weights, encoders, decoders, tokenizers, support assets and provider caches SHALL follow that folder without silently creating large home-drive caches.

#### Scenario: Choose a different drive
- **WHEN** model setup is initiated with a selected folder on another drive
- **THEN** downloads, partial assets and inference caches remain under that folder and the choice survives restarts

#### Scenario: Cancel native selection
- **WHEN** the directory picker is canceled
- **THEN** the selected location and existing data remain unchanged and model installation does not start

### Requirement: Compatible model reuse
Settings SHALL allow installing/selecting supported compatible models and reusing verified local assets. Choosing another location with existing current/default model data SHALL prompt for a verified move, destination reuse without moving or cancellation. Moves SHALL verify managed data before committing preferences and remove only unchanged unshared originals, preserving unrelated or externally changed files and other installations' references. Installation/verification SHALL remain separate from folder selection.

#### Scenario: Reuse an existing installation
- **WHEN** a folder containing verified compatible assets is selected
- **THEN** the app activates those assets without redownloading them and retains the previous assets if verification fails

#### Scenario: Move shared models
- **WHEN** model data is moved to an empty chosen folder
- **THEN** verified independent assets and this installation's references follow the new location while shared originals, foreign references and unrelated data remain in the original folder
