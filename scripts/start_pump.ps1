$repo = Get-Location
$logDir = Join-Path $repo 'log'
$pumpOut = Join-Path $logDir 'pump.log'
$pumpErr = Join-Path $logDir 'pump.err.log'

$proc = Start-Process uv `
    -ArgumentList 'run', 'python', 'src/watchers/pump.py' `
    -WindowStyle Hidden `
    -RedirectStandardOutput $pumpOut `
    -RedirectStandardError $pumpErr `
    -PassThru
    
$proc.Id | Out-File -FilePath 'event_pump.pid' -Encoding ascii
