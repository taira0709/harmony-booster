@echo off
set PORT=8501
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do taskkill /PID %%a /F
echo Stopped server on port %PORT% (if running).
pause
