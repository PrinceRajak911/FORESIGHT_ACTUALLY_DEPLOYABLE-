@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo First run detected. Starting setup...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo Starting FORESIGHT dashboard...
echo Open http://localhost:8501 in your browser.
echo Keep this window open while using the dashboard.
venv\Scripts\python.exe -m streamlit run app\streamlit_app.py --server.address=127.0.0.1 --server.port=8501
