' Launches auto_capture.ps1 with NO console window at all.
' wscript.exe allocates no console, and Run(..., 0, False) = hidden, no-wait.
' This is what the DayZMemoryAutoCapture scheduled task executes, so the
' 5-min capture never flashes a terminal window.
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("PROCESS")
scriptPath = env("USERPROFILE") & "\Dayz\dayz\dayz-memory\hooks\auto_capture.ps1"
sh.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """", 0, False
