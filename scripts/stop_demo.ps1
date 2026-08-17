# Stop demo containers but keep Postgres/Mosquitto volumes for inspection.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    docker compose down --remove-orphans
    Write-Host "Đã dừng demo containers. Dữ liệu volumes vẫn được giữ lại." -ForegroundColor Green
} finally {
    Pop-Location
}
