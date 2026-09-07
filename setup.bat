@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo FORESIGHT - First Time Setup
echo ==========================================

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3.12"
) else (
    set "PY=python"
)

%PY% --version
if errorlevel 1 (
    echo.
    echo Python 3.12 is required. Install it from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv venv
    if errorlevel 1 goto :error
)

echo Installing dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Running data pipeline...
venv\Scripts\python.exe src\run_pipeline.py
if errorlevel 1 goto :error

echo.
echo ==========================================
echo Setup complete.
echo Run run_dashboard.bat to start FORESIGHT.
echo ==========================================
pause
exit /b 0

:error
echo.
echo Setup failed. Read the error above.
pause
exit /b 1
