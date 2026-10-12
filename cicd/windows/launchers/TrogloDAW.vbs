' Launch TrogloDAW without a console window
Set fso = CreateObject("Scripting.FileSystemObject")
d = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = d
sh.Run """" & d & "\python\pythonw.exe"" """ & d & "\app\backend\app.py""", 0, False
