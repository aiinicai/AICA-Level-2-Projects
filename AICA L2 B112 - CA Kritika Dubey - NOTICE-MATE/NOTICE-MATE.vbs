' NOTICE-MATE - double-click to open the app in its own window (no Command Prompt windows).
' Closing the NOTICE-MATE window stops the app.
Option Explicit
Dim fso, sh, root, py, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
py = "pythonw"
If fso.FileExists(root & "\.venv\Scripts\pythonw.exe") Then py = """" & root & "\.venv\Scripts\pythonw.exe"""
If fso.FileExists(root & "\venv\Scripts\pythonw.exe") Then py = """" & root & "\venv\Scripts\pythonw.exe"""
sh.CurrentDirectory = root
cmd = py & " """ & root & "\scripts\desktop_launcher.py"""
If WScript.Arguments.Count > 0 Then cmd = cmd & " " & WScript.Arguments(0)
On Error Resume Next
sh.Run cmd, 0, False
If Err.Number <> 0 Then
  MsgBox "NOTICE-MATE could not start because Python was not found." & vbCrLf & _
         "Install Python 3.11+ (tick 'Add python.exe to PATH') and try again.", vbExclamation, "NOTICE-MATE"
End If
