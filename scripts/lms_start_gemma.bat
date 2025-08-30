@echo off
setlocal

REM Start Gemma via LM Studio CLI (lms)
REM Usage: scripts\lms_start_gemma.bat
REM Requires: .env.local with LLM_URL and LLM_MODEL

REM Move to project root (one level up from this script)
pushd "%~dp0\.."

REM Load shared env (required)
if exist ".env.local" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env.local") do (
    if not "%%A"=="" set "%%A=%%B"
  )
) else (
  echo [ERROR] .env.local not found at project root. Copy .env.local.example and set values.
  popd
  exit /b 1
)

REM Determine model strictly from .env.local (no args override)
if "%LLM_MODEL%"=="" (
  echo [ERROR] LLM_MODEL is not set. Define it in .env.local
  popd
  exit /b 1
)

REM Require LLM_URL from .env.local
if "%LLM_URL%"=="" (
  echo [ERROR] LLM_URL is not set. Define it in .env.local
  popd
  exit /b 1
)

where lms >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 'lms' CLI not found in PATH. Install LM Studio and ensure 'lms' is available.
  exit /b 1
)

echo [INFO] Checking if model is already loaded via 'lms ps'...
lms ps | findstr /I "%LLM_MODEL%" >nul 2>&1
if %errorlevel% equ 0 (
  echo [OK] '%LLM_MODEL%' already loaded. Skipping 'lms load'.
) else (
  echo [INFO] Loading model: %LLM_MODEL%
  lms load "%LLM_MODEL%"
)

echo [INFO] Ensuring LM Studio Local Server at %LLM_URL%
curl -s %LLM_URL%/v1/models >nul 2>&1
if %errorlevel% equ 0 (
  echo [OK] Server already running.
) else (
  lms server start
)

echo [INFO] Waiting for server to respond...
set /a attempts=60
:wait_server
curl -s %LLM_URL%/v1/models >nul 2>&1
if %errorlevel% equ 0 goto server_ok
set /a attempts=attempts-1
if %attempts% leq 0 goto server_fail
timeout /t 1 /nobreak >nul
goto wait_server

:server_ok
echo [OK] Server is up. /v1/models response:
curl -s %LLM_URL%/v1/models

echo.

exit /b 0

:server_fail
echo [ERROR] Could not reach %LLM_URL%/v1/models
exit /b 1

endlocal
