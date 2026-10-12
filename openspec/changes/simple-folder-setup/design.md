## Context

The current relocation API copies/verifies a folder but leaves the original as a recovery copy. Setup users must type absolute paths and choose between overlapping buttons. Storage is shared with the local catalog and model ownership manifests; existing opaque media tokens point at absolute files.

## Decisions

1. A user-triggered same-origin request opens the Windows Common Item Dialog with folder-only/filesystem options through stdlib ctypes. COM is initialized/released on that request thread. Cancel returns no selection and leaves settings unchanged; errors remain recoverable. Native initialization can be probed without displaying a dialog, and automated API/browser tests inject only the native selection boundary. Source platforms without the Windows picker provide an explicit manual-path fallback rather than silently changing storage.
2. Initial setup and Settings use the same concise folder controls. Choosing a different location prompts when current/default managed data exists, with Move existing data, Use folder without moving and Cancel. Installation/verification stays separate; model download status retains actual byte/rate ranges and subsequent readiness stages.
3. Moves stage and verify managed files, reject nested/nonempty conflicting destinations, commit the selected preference only after successful verification, and then remove only unchanged verified originals. Model co-owner references protect shared originals; foreign manifests/cache files and unrelated files do not move. Library managed audio/catalog/assets/inbox move together and relative recipes remain valid. Changed or undeletable originals are retained and reported after a successful destination switch, never turn a working move into misleading total failure.
4. Keep explicit recoverable copy relocation available internally; the simplified UI uses verified moves. Before source cleanup, update existing registered media paths from the old library root to their new verified locations. Empty old managed subdirectories may be pruned, never recursively delete arbitrary roots. Cancellation before commit preserves the original active location; the short preference/media/cleanup commit acknowledges cancellation only after it is consistent.
5. Exercise native probe, picker selection/cancel/error, detected-data prompts, move/no-move, destination conflict/interruption/shared/changed/unrelated retention, restart/playback/recipe and uninstall ownership. Keep synthetic libraries/models on the work drive. Required Actions repeat native installed workflows.

## Sources

Windows [Common Item Dialog](https://learn.microsoft.com/en-us/windows/win32/shell/common-file-dialog) and [folder-only options](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/ne-shobjidl_core-_fileopendialogoptions). Windows packaging needs no Tk, extra Python model package or Node runtime for the picker.
