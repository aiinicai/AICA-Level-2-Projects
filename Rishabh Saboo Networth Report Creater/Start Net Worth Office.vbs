Option Explicit
Dim files, shell, folder, python, program
Set files = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = files.GetParentFolderName(WScript.ScriptFullName)
python = files.BuildPath(folder, ".venv\Scripts\pythonw.exe")
program = Chr(34) & python & Chr(34) & " -c ""import networth; networth.desktop_entry()"""
If Not files.FileExists(python) Then
    MsgBox "Install the Python libraries using README.md before launching Net Worth Office.", 48, "Net Worth Office"
Else
    shell.CurrentDirectory = folder
    shell.Run program, 0, False
End If
