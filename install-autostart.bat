@echo off
cd /d "%~dp0"
set TASK_NAME=StockResearcher
set SCRIPT=%~dp0autostart.bat

echo Installing StockResearcher as a startup task...
echo App folder: %~dp0
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$action  = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + '%SCRIPT%' + '\"');" ^
  "$trigger = New-ScheduledTaskTrigger -AtLogOn;" ^
  "$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries;" ^
  "Register-ScheduledTask -TaskName '%TASK_NAME%' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null;" ^
  "Write-Host 'Task registered OK.'"

if errorlevel 1 (
    echo.
    echo ERROR: Could not create the scheduled task.
    echo Make sure you right-clicked and chose "Run as administrator".
    pause
    exit /b 1
)

echo.
echo Done! StockResearcher will start automatically 90 seconds after you log in.
echo.
echo To remove auto-start later, run: uninstall-autostart.bat
echo To start it right now without rebooting, double-click start.bat
echo.
pause
