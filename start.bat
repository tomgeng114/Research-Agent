@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Research-Agent — Starting Server
echo ============================================
echo.

REM Use E:\python.exe which has all dependencies installed
set PYTHON=E:\python.exe
if not exist "%PYTHON%" (
    echo [FAIL] E:\python.exe not found
    pause
    exit /b 1
)
echo [OK] Python: %PYTHON%
echo.

REM Check for .env file
if not exist ".env" (
    echo [!] .env file not found!
    echo     Creating from .env.example — please edit with your API key
    copy .env.example .env
    echo.
    pause
    exit /b 1
)
echo [OK] .env found
echo.

REM Initialize database
echo [OK] Initializing database...
%PYTHON% init_db.py
if errorlevel 1 (
    echo [FAIL] Database initialization failed
    pause
    exit /b 1
)

echo.
echo [OK] Starting server at http://127.0.0.1:8001
echo [OK] API docs at http://127.0.0.1:8001/docs
echo.
echo Press Ctrl+C to stop
echo ============================================
echo.

REM Start from C:\Users\Tom to avoid Python path issues
%PYTHON% -m uvicorn app.main:app --app-dir "%~dp0" --host 127.0.0.1 --port 8001 --reload

pause
