# Dừng demo localhost — CHỈ dừng PID do start_demo.ps1 ghi lại và thuộc project.
$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root ".demo/pids.json"
if (-not (Test-Path $PidFile)) {
    Write-Host "Không có PID file (.demo/pids.json) — demo chưa được start bởi script này." -ForegroundColor Yellow
    exit 0
}

$pids = Get-Content $PidFile -Raw | ConvertFrom-Json
$stopped = @()
foreach ($name in @("backend", "frontend", "edge")) {
    $procId = [int]$pids.$name
    if (-not $procId) { continue }
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if (-not $proc) { continue }

    # Xác minh command line thuộc project trước khi stop — không kill wildcard
    $cmd = $proc.Path
    $isOurs = $false
    try { $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction Stop).CommandLine } catch { $cmdline = "" }
    if ($cmdline -match [regex]::Escape($Root)) { $isOurs = $true }
    elseif ($cmd -match [regex]::Escape($Root)) { $isOurs = $true }

    if ($isOurs) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        $stopped += "$name (pid $procId)"
    } else {
        Write-Host "Bỏ qua $name pid $procId — không thuộc project ($cmd)" -ForegroundColor Yellow
    }
}

Remove-Item $PidFile -ErrorAction SilentlyContinue
if ($stopped.Count -gt 0) {
    Write-Host "Đã dừng: $($stopped -join ', ')" -ForegroundColor Green
} else {
    Write-Host "Không có process demo nào đang chạy." -ForegroundColor Green
}
