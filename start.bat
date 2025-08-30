@echo off
setlocal

echo.
echo ================================
echo  Back2Task Starting up...
echo ================================
echo.

REM --- 1. Setup Environment ---
cd /d "%~dp0"
set "PYTHONPATH=%cd%"

REM --- Load common env from .env.local (required) ---
if exist ".env.local" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env.local") do (
        if not "%%A"=="" set "%%A=%%B"
    )
    echo [SETUP] Loaded .env.local
) else (
    echo [ERROR] .env.local not found at project root.
    endlocal
    exit /b 1
)

REM Required vars check (fail fast)
if not defined LLM_URL (
    echo [ERROR] LLM_URL must be set in .env.local
    endlocal
    exit /b 1
)
if not defined LLM_MODEL (
    echo [ERROR] LLM_MODEL must be set in .env.local
    endlocal
    exit /b 1
)

echo [SETUP] Checking for virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Virtual environment not found. Creating...
    python -m venv venv
) else (
    echo [SETUP] Virtual environment found.
)

echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat

echo [SETUP] Installing/Verifying dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies from requirements.txt.
    endlocal
    exit /b 1
)

REM --- 2. Cleanup Old Processes ---
echo [CLEANUP] Checking for existing processes...

REM Clean up old PID files
if exist "api_server.pid" (
    echo [CLEANUP] Removing old API server PID file
    del "api_server.pid" >nul 2>&1
)
if exist "event_pump.pid" (
    echo [CLEANUP] Removing old event pump PID file
    del "event_pump.pid" >nul 2>&1
)

REM Kill process on port 5577 (API Server)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5577"') do (
    if "%%a" NEQ "0" (
        echo [CLEANUP] Stopping existing process on port 5577 (PID: %%a)
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM Kill old pump process by window title
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Back2Task-Pump" /T >nul 2>&1
taskkill /F /IM uvicorn.exe /FI "WINDOWTITLE eq Back2Task-API" /T >nul 2>&1


echo [CLEANUP] Cleanup complete.

REM --- 3. Start Services ---
echo [START] Starting FastAPI server...

REM Use PowerShell to start process and capture PID
powershell -Command "$proc = Start-Process python -ArgumentList '-m', 'uvicorn', 'api.main:app', '--reload', '--port', '5577', '--host', '127.0.0.1' -WindowStyle Hidden -PassThru; $proc.Id | Out-File -FilePath 'api_server.pid' -Encoding ascii"

echo [START] Waiting for server to respond...
:wait_for_server
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:5577/status >nul
if %errorlevel% neq 0 (
    echo -n .
    goto wait_for_server
)
echo.
echo [START] FastAPI server started successfully.

echo [START] Starting Event Pump...

REM Use PowerShell to start pump and capture PID
powershell -Command "$proc = Start-Process python -ArgumentList 'watchers/pump.py', '--api-url', 'http://127.0.0.1:5577/events', '--interval', '3.0' -WindowStyle Hidden -PassThru; $proc.Id | Out-File -FilePath 'event_pump.pid' -Encoding ascii"

REM A simple sleep to assume the pump starts.
timeout /t 3 /nobreak >nul
echo [START] Event Pump started.

REM --- 4. Status Check ---
echo [STATUS] Checking for LLM server...
curl -s %LLM_URL%/v1/models >nul
if %errorlevel% equ 0 (
    set "LLM_STATUS=Available (%LLM_URL%)"
) else (
    set "LLM_STATUS=Unreachable (AI disabled)"
)

echo.
echo ================================
echo  Back2Task is now running!
echo ================================
echo.
echo   - API Server: http://127.0.0.1:5577
echo   - Event Pump: Running
echo   - LLM Server: %LLM_STATUS%
echo.
echo To stop the services, run 'stop.bat'
echo.

endlocal
