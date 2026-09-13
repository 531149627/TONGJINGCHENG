Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = scriptDir
ws.Run "cmd /c """ & scriptDir & "\Ë«»÷Æô¶¯×À³è.bat""", 0, False
