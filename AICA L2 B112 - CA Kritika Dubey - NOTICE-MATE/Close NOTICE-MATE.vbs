' Stops NOTICE-MATE if it is still running in the background.
Option Explicit
Dim fso, sh, root
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "wscript """ & root & "\NOTICE-MATE.vbs"" --stop", 0, False
