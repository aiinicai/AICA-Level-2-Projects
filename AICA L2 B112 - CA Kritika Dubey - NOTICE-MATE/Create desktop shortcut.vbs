' Puts a "NOTICE-MATE" shortcut on your desktop. Run once.
Option Explicit
Dim fso, sh, root, lnk
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
Set lnk = sh.CreateShortcut(sh.SpecialFolders("Desktop") & "\NOTICE-MATE.lnk")
lnk.TargetPath = sh.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\wscript.exe"
lnk.Arguments = """" & root & "\NOTICE-MATE.vbs"""
lnk.WorkingDirectory = root
lnk.IconLocation = sh.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\shell32.dll,21"
lnk.Description = "Open NOTICE-MATE"
lnk.Save
MsgBox "A NOTICE-MATE shortcut has been placed on your desktop.", vbInformation, "NOTICE-MATE"
