' Launch TrogloDAW without a console window (compatible file name retained)
Set fso = CreateObject("Scripting.FileSystemObject")
d = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = d
sh.Run """" & d & "\python\pythonw.exe"" """ & d & "\app\backend\app.py""", 0, False
