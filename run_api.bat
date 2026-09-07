@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo Starting FORESIGHT API...
echo API: http://localhost:8000
echo Docs: http://localhost:8000/docs
venv\Scripts\python.exe -m uvicorn service.api:app --host 127.0.0.1 --port 8000
