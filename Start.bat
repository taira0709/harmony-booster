@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo [INFO] creating venv...
  python -m venv .venv
)

set PY=.\.venv\Scripts\python.exe
set MAIN=app.py
if not exist "%MAIN%" (
  rem 互換: 旧名が残っていればそちらを使う
  set MAIN=app_streamlit_ms.py
)

%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt

echo [INFO] starting %MAIN% ...
"%PY%" -m streamlit run "%MAIN%" --server.port 8501

echo.
echo [DONE] Press any key to close...
pause >nul
