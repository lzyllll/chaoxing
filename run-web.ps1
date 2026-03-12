param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $projectRoot "frontend"

if (-not (Test-Path $frontendDir)) {
    throw "frontend directory not found: $frontendDir"
}

$backendCommand = @"
cd '$projectRoot'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv not found. Please install uv first.'
}

Write-Host 'Starting backend with uv...'
uv sync
uv run --python 3.13 -m uvicorn web_api:app --host 127.0.0.1 --port $BackendPort --reload
"@

$frontendCommand = @"
cd '$frontendDir'
if (-not (Test-Path 'node_modules')) {
    npm install
}
npm run dev -- --host 127.0.0.1 --port $FrontendPort
"@

Start-Process powershell -ArgumentList @('-NoExit', '-Command', $backendCommand) | Out-Null
Start-Process powershell -ArgumentList @('-NoExit', '-Command', $frontendCommand) | Out-Null

Write-Host "Backend started: http://127.0.0.1:$BackendPort"
Write-Host "Frontend started: http://127.0.0.1:$FrontendPort"
Write-Host "Started in two new PowerShell windows."
