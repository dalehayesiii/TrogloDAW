; Music Maker - per-user Windows installer (no admin required)
Unicode true
SetCompressor /SOLID lzma
SetCompressorDictSize 64
ManifestDPIAware true
RequestExecutionLevel user

!define APPNAME "Music Maker"
!define APPKEY "MusicMaker"
!ifndef VERSION
  !define VERSION "0.0.0"
!endif
; Paths can be passed by build.sh:  makensis -DSTAGE=... -DOUTFILE=... -DINSTALL_DIR=... -DLIBRARY_DIR=...
!ifndef STAGE
  !define STAGE "work\stage\MusicMaker"
!endif
!ifndef OUTFILE
  !define OUTFILE "MusicMaker-Setup.exe"
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

!define MUI_ICON "${STAGE}\musicmaker.ico"
!define MUI_UNICON "${STAGE}\musicmaker.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "This will install ${APPNAME} on your computer.$\r$\n$\r$\nIt includes its own copy of Python, so you don't need to install anything else. No administrator rights are needed.$\r$\n$\r$\nYour recordings, beats and mixes are saved in Documents\MusicMaker\library.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APPNAME}"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!define MUI_FINISHPAGE_TEXT "${APPNAME} is installed.$\r$\n$\r$\nUse the 'Music Maker' shortcut on your Desktop or Start Menu. It opens in your web browser (the first start can take up to a minute).$\r$\n$\r$\nLibrary folder: Documents\MusicMaker\library"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

!macro StopRunning
  ; stop any Music Maker instance started from this install folder (files would be locked)
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
  SetOutPath "$INSTDIR"
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\app\backend\app.py"' "$INSTDIR\musicmaker.ico" 0 SW_SHOWNORMAL "" "Make music: voices, beats, mixes"
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\python\pythonw.exe" '"$INSTDIR\app\backend\app.py"' "$INSTDIR\musicmaker.ico" 0 SW_SHOWNORMAL "" "Make music: voices, beats, mixes"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME} (console, troubleshooting).lnk" "$INSTDIR\Music Maker (console).bat" "" "$INSTDIR\musicmaker.ico" 0
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Music Maker Library folder.lnk" "${LIBRARY_DIR}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall ${APPNAME}.lnk" "$INSTDIR\Uninstall.exe"

  ; uninstaller + Apps & Features entry (per-user)
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\${APPKEY}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "musicmaker"
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
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
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
