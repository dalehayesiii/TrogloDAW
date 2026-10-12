; TrogloDAW - per-user Windows installer (legacy install keys/roots retained)
Unicode true
SetCompressor /SOLID lzma
SetCompressorDictSize 64
ManifestDPIAware true
RequestExecutionLevel user

!define APPNAME "TrogloDAW"
!define APPKEY "MusicMaker"
!ifndef VERSION
  !define VERSION "0.0.0"
!endif
; Paths can be passed by build.sh:  makensis -DSTAGE=... -DOUTFILE=... -DINSTALL_DIR=... -DLIBRARY_DIR=...
!ifndef STAGE
  !define STAGE "work\stage\MusicMaker"
!endif
!ifndef OUTFILE
  !define OUTFILE "TrogloDAW-Setup.exe"
!endif
!ifndef INSTALL_DIR
  !define INSTALL_DIR "$LOCALAPPDATA\MusicMaker"
!endif
!ifndef LIBRARY_DIR
  !define LIBRARY_DIR "$DOCUMENTS\MusicMaker\library"
!endif
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}"

Name "${APPNAME}"
OutFile "${OUTFILE}"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKCU "Software\${APPKEY}" "InstallDir"
BrandingText "${APPNAME} ${VERSION}"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "FileDescription" "${APPNAME} Setup"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "Personal use"

!include "MUI2.nsh"
!include "WordFunc.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "nsDialogs.nsh"
!include "FileFunc.nsh"
Var RemoveModels
Var ModelsCheckbox

!define MUI_ICON "${STAGE}\musicmaker.ico"
!define MUI_UNICON "${STAGE}\musicmaker.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "This will install ${APPNAME} on your computer.$\r$\n$\r$\nIt includes its own Python runtime. No administrator rights are needed. Initial app setup installs a local model into a folder you choose.$\r$\n$\r$\nInitial library folder: ${LIBRARY_DIR}$\r$\nYou can choose another library in Settings.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APPNAME}"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!define MUI_FINISHPAGE_TEXT "${APPNAME} is installed.$\r$\n$\r$\nUse the '${APPNAME}' shortcut on your Desktop or Start Menu. It opens in your web browser. Initial setup installs a local model into the folder you choose.$\r$\n$\r$\nLibrary folder: ${LIBRARY_DIR}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
UninstPage custom un.ModelRemovalPage un.ModelRemovalLeave
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

!macro StopRunning
  ; stop any app instance started from this compatible install folder (files would be locked)
  nsExec::Exec 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Get-Process python,pythonw,ffmpeg-win-x86_64-v7.1 -ErrorAction SilentlyContinue | Where-Object { $$_.Path -like \"$INSTDIR\*\" } | Stop-Process -Force"'
  Pop $0
  Sleep 500
!macroend

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "${APPNAME} requires 64-bit Windows 10 or 11."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "${APPNAME} requires Windows 10 or 11."
    Abort
  ${EndIf}
FunctionEnd

Function LaunchApp
  SetOutPath "$INSTDIR"
  Exec '"$INSTDIR\python\pythonw.exe" "$INSTDIR\app\backend\app.py"'
FunctionEnd

Function un.onInit
  StrCpy $RemoveModels ${BST_CHECKED}
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/KEEP_MODELS" $1
  ${IfNot} ${Errors}
    StrCpy $RemoveModels ${BST_UNCHECKED}
  ${EndIf}
FunctionEnd

Function un.ModelRemovalPage
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}
  ${NSD_CreateLabel} 0 0 100% 40u "Your song libraries are preserved. Choose whether to remove model assets installed by this application. Shared, reused, changed and unrelated files are preserved."
  Pop $0
  ${NSD_CreateCheckbox} 0 50u 100% 20u "Remove installed model assets"
  Pop $ModelsCheckbox
  ${If} $RemoveModels == ${BST_CHECKED}
    ${NSD_Check} $ModelsCheckbox
  ${EndIf}
  nsDialogs::Show
FunctionEnd

Function un.ModelRemovalLeave
  ${NSD_GetState} $ModelsCheckbox $RemoveModels
FunctionEnd

Section "Install"
  !insertmacro StopRunning
  ; clean old runtime so upgrades never mix package versions (library/config are kept)
  RMDir /r "$INSTDIR\python"

  SetOutPath "$INSTDIR"
  File "${STAGE}\musicmaker.ico"
  File "${STAGE}\MusicMaker.vbs"
  File "${STAGE}\mm.bat"
  File "${STAGE}\Music Maker (console).bat"
  SetOutPath "$INSTDIR\app"
  File /r "${STAGE}\app\*.*"
  SetOutPath "$INSTDIR\python"
  File /r "${STAGE}\python\*.*"

  ; library in the user's Documents (handles OneDrive-redirected Documents too)
  CreateDirectory "${LIBRARY_DIR}\inbox"
  IfFileExists "$INSTDIR\app\config.json" config_done
    ${WordReplace} "${LIBRARY_DIR}" "\" "/" "+" $1
    FileOpen $0 "$INSTDIR\app\config.json" w
    FileWriteWord $0 0xFEFF
    FileWriteUTF16LE $0 '{$\r$\n  "library_dir": "$1"$\r$\n}$\r$\n'
    FileClose $0
  config_done:

  ; precompile Python files so the first launch is fast (also a smoke test of the runtime)
  DetailPrint "Optimizing (precompiling Python files, about a minute)..."
  nsExec::ExecToLog '"$INSTDIR\python\python.exe" -m compileall -q -j 0 "$INSTDIR\python\Lib\site-packages" "$INSTDIR\app"'
  Pop $0
  DetailPrint "compileall exit code: $0"

  ; shortcuts (pythonw = no console window)
  ; Replace only known old shortcuts, retaining unrelated custom Start Menu entries.
  Delete "$DESKTOP\Music Maker.lnk"
  Delete "$SMPROGRAMS\Music Maker\Music Maker.lnk"
  Delete "$SMPROGRAMS\Music Maker\Music Maker (console, troubleshooting).lnk"
  Delete "$SMPROGRAMS\Music Maker\Music Maker Library folder.lnk"
  Delete "$SMPROGRAMS\Music Maker\Uninstall Music Maker.lnk"
  RMDir "$SMPROGRAMS\Music Maker"
  SetOutPath "$INSTDIR"
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\app\backend\app.py"' "$INSTDIR\musicmaker.ico" 0 SW_SHOWNORMAL "" "Make music: voices, beats, mixes"
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\app\backend\app.py"' "$INSTDIR\musicmaker.ico" 0 SW_SHOWNORMAL "" "Make music: voices, beats, mixes"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME} (console, troubleshooting).lnk" "$INSTDIR\Music Maker (console).bat" "" "$INSTDIR\musicmaker.ico" 0
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME} Library folder.lnk" "${LIBRARY_DIR}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" "$INSTDIR\Uninstall.exe"

  ; uninstaller + Apps & Features entry (per-user)
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\${APPKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "TrogloDAW"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\musicmaker.ico"
  WriteRegStr HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "${UNINSTKEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "EstimatedSize" 460000
SectionEnd

Section "Uninstall"
  !insertmacro StopRunning
  ${If} $RemoveModels == ${BST_CHECKED}
    nsExec::ExecToLog '"$INSTDIR\python\python.exe" "$INSTDIR\app\backend\storage.py" "$INSTDIR\app\config.local.json"'
    Pop $0
    ${If} $0 != 0
      MessageBox MB_ICONSTOP "Model cleanup could not safely complete. Your app and libraries are still present. Retry uninstall with model removal unchecked to retain the model files."
      Abort
    ${EndIf}
  ${EndIf}
  Delete "$DESKTOP\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME} (console, troubleshooting).lnk"
  Delete "$SMPROGRAMS\${APPNAME}\${APPNAME} Library folder.lnk"
  Delete "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk"
  RMDir "$SMPROGRAMS\${APPNAME}"
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\app"
  Delete "$INSTDIR\musicmaker.ico"
  Delete "$INSTDIR\MusicMaker.vbs"
  Delete "$INSTDIR\mm.bat"
  Delete "$INSTDIR\Music Maker (console).bat"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${UNINSTKEY}"
  DeleteRegKey HKCU "Software\${APPKEY}"
  IfSilent +2
    MessageBox MB_ICONINFORMATION "${APPNAME} was removed.$\r$\n$\r$\nYour recordings and mixes were kept in:$\r$\n${LIBRARY_DIR}"
SectionEnd
