@echo off
REM Called by Task Scheduler on login. Waits 90 seconds for the network
REM to come up, then starts the StockResearcher server.
timeout /t 90 /nobreak >nul
cd /d "%~dp0"
call start.bat
