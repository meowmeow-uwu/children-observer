# Start the laptop/server services only.  A real Raspberry Pi must be the
# only Edge for its camera_id, so this deliberately excludes Compose's demo
# `edge` service.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    docker compose up --build -d mqtt db migrate seed backend frontend

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
        throw "Backend chua san sang sau 3 phut. Xem: docker compose logs backend migrate seed mqtt"
    }

    docker compose ps
    Write-Host ""
    Write-Host "Server stack da san sang (khong chay Edge demo)" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
    Write-Host "Backend:  http://localhost:8007" -ForegroundColor Green
    Write-Host "MQTT LAN: <IP-laptop>:1883" -ForegroundColor Green
    Write-Host "Demo login: demo@childrenobserver.org / demo12345" -ForegroundColor Yellow
} finally {
    Pop-Location
}
