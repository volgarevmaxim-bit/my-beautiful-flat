' open_in_firefox.vbs
' Runs open_in_firefox.bat hidden (window style 0, no console flash)
' when the myflat: protocol is invoked. The registry entry points to
' THIS file, not to the .bat directly.
Option Explicit
Dim sh, fso, p, u, cmd
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
p = fso.GetParentFolderName(WScript.ScriptFullName)
If WScript.Arguments.Count = 0 Then WScript.Quit 1
u = WScript.Arguments(0)
' Quotes would break the command string; the .bat re-validates the URL.
u = Replace(u, Chr(34), "")
cmd = "cmd /c " & Chr(34) & Chr(34) & p & "\open_in_firefox.bat" & Chr(34) & " " & Chr(34) & u & Chr(34) & Chr(34)
sh.Run cmd, 0, False
