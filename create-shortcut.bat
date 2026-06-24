@echo off
cd /d "%~dp0"
set APP_DIR=%~dp0
set ICO=%APP_DIR%StockResearcher.ico
set TARGET=%APP_DIR%start.bat

echo Creating StockResearcher shortcut on your Desktop...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desktop = $ws.SpecialFolders('Desktop');" ^
  "$s = $ws.CreateShortcut([System.IO.Path]::Combine($desktop, 'StockResearcher.lnk'));" ^
  "$s.TargetPath = '%TARGET%';" ^
  "$s.WorkingDirectory = '%APP_DIR%';" ^
  "$s.IconLocation = '%ICO%';" ^
  "$s.Description = 'Launch StockResearcher';" ^
  "$s.Save();" ^
  "Write-Host ('Shortcut saved to: ' + $desktop)"

if errorlevel 1 (
    echo ERROR: Could not create shortcut.
    pause
    exit /b 1
)

echo.
echo Done! Look for StockResearcher on your Desktop.
echo.
pause
