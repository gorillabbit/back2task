@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ================================
echo   Back2Task Stopping...
echo ================================
echo.

set "stopped_count=0"

REM --- Stop processes using PID files ---
echo [STOP] Stopping processes using PID files...

if exist "api_server.pid" (
    set /p API_PID=<api_server.pid
    echo   - Stopping API Server PID: !API_PID!
    taskkill /F /PID !API_PID! >nul 2>&1
    if not errorlevel 1 (
        echo   - API Server stopped using PID file
        set /a stopped_count+=1
    )
    del "api_server.pid" >nul 2>&1
)

if exist "event_pump.pid" (
    set /p PUMP_PID=<event_pump.pid
    echo   - Stopping Event Pump PID: !PUMP_PID!
    taskkill /F /PID !PUMP_PID! >nul 2>&1
    if not errorlevel 1 (
        echo   - Event Pump stopped using PID file
        set /a stopped_count+=1
    )
    del "event_pump.pid" >nul 2>&1
)

REM --- Stop API Server (by port) ---
echo [STOP] Stopping API server on port 5577...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5577"') do (
    if "%%a" NEQ "0" (
        echo   - Stopping process PID: %%a
        taskkill /F /PID %%a >nul 2>&1
        if not errorlevel 1 (
            echo   - API Server stopped successfully
            set /a stopped_count+=1
        )
    )
)

REM --- Stop processes by window title ---
echo [STOP] Stopping Event Pump by window title...
taskkill /F /FI "WINDOWTITLE eq Back2Task-Pump" /T >nul 2>&1
if not errorlevel 1 (
    echo   - Event Pump stopped by window title
    set /a stopped_count+=1
)

echo [STOP] Stopping API Server by window title...
taskkill /F /FI "WINDOWTITLE eq Back2Task-API" /T >nul 2>&1
if not errorlevel 1 (
    echo   - API Server stopped by window title
    set /a stopped_count+=1
)

REM --- Force stop all python processes as last resort ---
echo [STOP] Force stopping all python processes...
taskkill /F /IM python.exe >nul 2>&1
if not errorlevel 1 (
    echo   - All python processes stopped
    set /a stopped_count+=1
) else (
    echo   - No python processes found
)

echo.
if %stopped_count% gtr 0 (
    echo ================================
    echo   Back2Task stopped successfully
    echo ================================
) else (
    echo ================================
    echo   No Back2Task processes found
    echo ================================
)
echo.
echo To start the services again, run 'start.bat'
echo.

endlocal