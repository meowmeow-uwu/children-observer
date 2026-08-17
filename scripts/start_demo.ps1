# Start the complete demo stack from a fresh database through Docker Compose.
# Migration and idempotent demo seeding are Compose services, so this script
# does not create local Python/Node processes that can drift from production.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    foreach ($asset in @("weights/roi_detection/best.onnx", "module_edge_firmware/test_video.mp4")) {
        if (-not (Test-Path $asset)) { throw "Thiếu asset bắt buộc: $asset" }
    }

    docker compose up --build -d

    $deadline = (Get-Date).AddMinutes(3)
    do {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8007/healthz" -TimeoutSec 3
            if ($health.status -eq "ok") { break }
        } catch {}
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    if (-not $health -or $health.status -ne "ok") {
        docker compose ps
        throw "Backend chưa sẵn sàng sau 3 phút. Xem: docker compose logs backend migrate seed edge"
    }

    docker compose ps
    Write-Host ""
    Write-Host "AI Child Observer demo đã sẵn sàng" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
    Write-Host "Backend:  http://localhost:8007" -ForegroundColor Green
    Write-Host "Demo login: demo@childrenobserver.org / demo12345" -ForegroundColor Yellow
    Write-Host "Dừng demo: .\scripts\stop_demo.ps1" -ForegroundColor Gray
} finally {
    Pop-Location
}
