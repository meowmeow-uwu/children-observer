# Khởi động demo localhost: backend (8007) + edge AI + frontend (5173).
# Không tự cài dependency; kiểm tra port trước; chỉ dừng process do script tạo.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $Root ".demo"
$LogDir = Join-Path $RunDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$PidFile = Join-Path $RunDir "pids.json"
$pids = @{}

function Test-Port-Free([int]$port) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return $null -eq $listener
}

function Fail-Cleanup([string]$msg) {
    Write-Host "FAIL: $msg" -ForegroundColor Red
    & (Join-Path $PSScriptRoot "stop_demo.ps1")
    exit 1
}

# 1. Kiểm tra port
if (-not (Test-Port-Free 8007)) { Fail-Cleanup "Port 8007 đang bị chiếm (backend) — không kill process lạ." }
if (-not (Test-Port-Free 5173)) { Fail-Cleanup "Port 5173 đang bị chiếm (frontend) — không kill process lạ." }

# 2. Kiểm tra asset bắt buộc
if (-not (Test-Path (Join-Path $Root "weights/roi_detection/best.onnx"))) { Fail-Cleanup "Thiếu weights/roi_detection/best.onnx" }
if (-not (Test-Path (Join-Path $Root "module_edge_firmware/test_video.mp4"))) { Fail-Cleanup "Thiếu module_edge_firmware/test_video.mp4" }
if (-not (Test-Path (Join-Path $Root "frontend/package.json"))) { Fail-Cleanup "Thiếu frontend/package.json" }

Push-Location $Root

# 3. Backend
$env:DATABASE_URL = "sqlite:///$($Root -replace '\\','/')/demo_local.db"
$backend = Start-Process -FilePath (Join-Path $Root ".venv/Scripts/python.exe") `
    -ArgumentList "-m", "uvicorn", "module_backend_infra.main:app", "--host", "127.0.0.1", "--port", "8007" `
    -WorkingDirectory $Root -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "backend.log") -RedirectStandardError (Join-Path $LogDir "backend.err.log")
$pids["backend"] = $backend.Id

# 4. Frontend (Vite dev server — chạy node trực tiếp để PID thuộc project)
$frontend = Start-Process -FilePath "node" `
    -ArgumentList (Join-Path $Root "frontend/node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--port", "5173" `
    -WorkingDirectory (Join-Path $Root "frontend") -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "frontend.log") -RedirectStandardError (Join-Path $LogDir "frontend.err.log")
$pids["frontend"] = $frontend.Id

# 5. Edge AI (demo pipeline)
$env:EDGE_ONNX_INTRA_THREADS = "8"
$env:EDGE_ALERT_COOLDOWN_SECONDS = "5"
$edge = Start-Process -FilePath (Join-Path $Root ".venv/Scripts/python.exe") `
    -ArgumentList "-m", "module_edge_firmware.demo_stream" `
    -WorkingDirectory $Root -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "edge.log") -RedirectStandardError (Join-Path $LogDir "edge.err.log")
$pids["edge"] = $edge.Id

$pids | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

# 6. Health checks (tối đa 60s)
$deadline = (Get-Date).AddSeconds(60)
$backendOk = $false; $frontendOk = $false; $edgeOk = $false
while ((Get-Date) -lt $deadline) {
    if (-not $backendOk) {
        try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:8007/" -TimeoutSec 2 -UseBasicParsing; $backendOk = $r.StatusCode -eq 200 } catch {}
    }
    if (-not $frontendOk) {
        try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -TimeoutSec 2 -UseBasicParsing; $frontendOk = $r.StatusCode -eq 200 } catch {}
    }
    if (-not $edgeOk) {
        try {
            # loguru ghi ra stderr → edge.err.log; stdout → edge.log
            $log = Get-Content (Join-Path $LogDir "edge.err.log") -ErrorAction SilentlyContinue -Raw
            $log += Get-Content (Join-Path $LogDir "edge.log") -ErrorAction SilentlyContinue -Raw
            if ($log -match "Demo video opened|Relay WS connected|Video loop #") { $edgeOk = $true }
        } catch {}
    }
    if ($backendOk -and $frontendOk -and $edgeOk) { break }
    Start-Sleep -Milliseconds 500
}

if (-not $backendOk) { Fail-Cleanup "Backend không health-check được — xem .demo/logs/backend.log" }
if (-not $frontendOk) { Fail-Cleanup "Frontend không health-check được — xem .demo/logs/frontend.log" }
if (-not $edgeOk) { Fail-Cleanup "Edge không khởi động được — xem .demo/logs/edge.log" }

Pop-Location

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  AI Child Observer — DEMO READY" -ForegroundColor Green
Write-Host "  URL:  http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8007  (pid $($pids.backend))" -ForegroundColor Gray
Write-Host "  Edge AI:  pid $($pids.edge)" -ForegroundColor Gray
Write-Host "  Logs: $LogDir" -ForegroundColor Gray
Write-Host "  Dừng:  .\scripts\stop_demo.ps1" -ForegroundColor Gray
Write-Host "==============================================" -ForegroundColor Cyan
