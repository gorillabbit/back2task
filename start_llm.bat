@echo off
setlocal

rem Launch LM Studio local server using CLI
if "%LMSTUDIO_CLI%"=="" (
    set "CLI=lmstudio"
) else (
    set "CLI=%LMSTUDIO_CLI%"
)

if "%LLM_MODEL%"=="" (
    set "MODEL=google/gemma-3-4b"
) else (
    set "MODEL=%LLM_MODEL%"
)

if "%LLM_PORT%"=="" (
    set "PORT=1234"
) else (
    set "PORT=%LLM_PORT%"
)

if "%LLM_HOST%"=="" (
    set "HOST=127.0.0.1"
) else (
    set "HOST=%LLM_HOST%"
)

echo Starting LM Studio server (model: %MODEL%, port: %PORT%)...
where %CLI% >nul 2>&1
if errorlevel 1 (
    echo LM Studio CLI '%CLI%' not found. Install the CLI or set LMSTUDIO_CLI.
    exit /b 1
)

start "Back2Task-LLM" /b %CLI% start --model "%MODEL%" --host "%HOST%" --port %PORT%
endlocal
