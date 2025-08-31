$repo = Get-Location
$logDir = Join-Path $repo 'log'
$apiOut = Join-Path $logDir 'api.log'
$apiErrOut = Join-Path $logDir 'api.err.log'

$proc = Start-Process uv `
    -ArgumentList 'run', 'uvicorn', 'api.main:app', '--reload', '--port', '5577', '--host', '127.0.0.1' `
    -WindowStyle Hidden `
    -RedirectStandardOutput $apiOut `
    -RedirectStandardError $apiErrOut `
    -PassThru

$proc.Id | Out-File -FilePath 'api_server.pid' -Encoding ascii
