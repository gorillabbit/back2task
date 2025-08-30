@echo off
setlocal

where lms >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 'lms' CLI not found in PATH.
  exit /b 1
)

REM Move to project root
pushd "%~dp0\.."

REM Load env (required)
if exist ".env.local" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env.local") do (
    if not "%%A"=="" set "%%A=%%B"
  )
) else (
  echo [ERROR] .env.local not found at project root.
  popd
  exit /b 1
)

if not defined LLM_MODEL (
  echo [ERROR] LLM_MODEL is not set in .env.local
  popd
  exit /b 1
)

echo [INFO] Unloading model: %LLM_MODEL% (best-effort)...
lms unload "%LLM_MODEL%" >nul 2>&1

echo [INFO] Stopping LM Studio Local Server...
lms server stop
if %errorlevel% equ 0 (
  echo [OK] Stopped.
) else (
  echo [WARN] Stop command returned a non-zero code.
)

popd
endlocal
