@echo off
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://python.org and try again.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo First run: creating virtual environment...
    python -m venv .venv
    echo Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt --quiet
    echo.
)

echo Starting StockResearcher...
echo.
echo Open your browser to:
echo   This machine:  http://localhost:8000
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set ip=%%a
    goto :found
)
:found
echo   Local network: http://%ip: =%:8000
echo.
echo Press Ctrl+C to stop.
echo.
.venv\Scripts\python app.py
pause
