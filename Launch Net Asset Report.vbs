Option Explicit
Dim sh, fs, root, python, app, command, logFile
Set sh = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
root = fs.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root
python = root & "\.venv\Scripts\pythonw.exe"
app = root & "\net_asset_report.py"
logFile = root & "\launcher_used.log"
If fs.FileExists(python) And fs.FileExists(app) Then
    Dim logStream
    Set logStream = fs.OpenTextFile(logFile, 2, True)
    logStream.WriteLine "Launcher used: " & Now & vbCrLf & "Python: " & python & vbCrLf & "App: " & app
    logStream.Close
    sh.Environment("Process")("PYTHONPATH") = root
    command = Chr(34) & python & Chr(34) & " -B " & Chr(34) & app & Chr(34)
Else
    MsgBox "Current application files or virtual environment are missing." & vbCrLf & _
           "Run Install Dependencies.bat in this folder first.", 48, "Net Asset Report"
    WScript.Quit 1
End If
sh.Run command, 0, False
