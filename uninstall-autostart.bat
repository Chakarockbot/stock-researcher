@echo off
set TASK_NAME=StockResearcher

echo Removing StockResearcher from startup tasks...

schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

if errorlevel 1 (
    echo Task not found ^(may have already been removed^).
) else (
    echo Done. StockResearcher will no longer start automatically on login.
)
echo.
pause
