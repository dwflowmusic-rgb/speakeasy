Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

ScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
objShell.Run Chr(34) & ScriptDir & "\juris-transcritor-fast.bat" & Chr(34), 0

Set objShell = Nothing
Set objFSO = Nothing
