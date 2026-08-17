' Starts CMA Pro Builder without a console window.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
sh.Run "CMA-Pro-Builder.exe", 0, False
