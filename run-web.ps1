$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $projectRoot "frontend"
$backendConfig = Join-Path $projectRoot "backend.ini"
$backendExample = Join-Path $projectRoot "backend.example.ini"
$frontendEnv = Join-Path $frontendDir ".env"
$frontendEnvExample = Join-Path $frontendDir ".env.example"

if (-not (Test-Path $frontendDir)) {
    throw "frontend directory not found: $frontendDir"
}

$backendCommand = @"
cd '$projectRoot'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv not found. Please install uv first.'
}

Write-Host 'Syncing backend dependencies with uv...'
uv sync
Write-Host 'Starting backend with uvicorn (chaoxing.web.app:app)...'
uv run -m uvicorn chaoxing.web.app:app --host 127.0.0.1 --port 8000 --reload
"@

$frontendCommand = @"
cd '$frontendDir'
if (-not (Test-Path 'node_modules')) {
    npm install
}
npm run dev
"@

Start-Process powershell -ArgumentList @('-NoExit', '-Command', $backendCommand) | Out-Null
Start-Process powershell -ArgumentList @('-NoExit', '-Command', $frontendCommand) | Out-Null

Write-Host "Backend config: $backendConfig"
if (-not (Test-Path $backendConfig) -and (Test-Path $backendExample)) {
    Write-Host "Tip: copy $backendExample to $backendConfig to customize backend settings."
}

Write-Host "Frontend config: $frontendEnv"
if (-not (Test-Path $frontendEnv) -and (Test-Path $frontendEnvExample)) {
    Write-Host "Tip: copy $frontendEnvExample to $frontendEnv to customize frontend settings."
}

Write-Host "Backend health: http://127.0.0.1:8000/api/health"
Write-Host "Frontend URL: http://127.0.0.1:5173"
Write-Host "Started frontend and backend in two new PowerShell windows."
