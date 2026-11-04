# Simulasi Data Immunity (untuk video demo)
# Membuktikan data di Named Volume `queue-db-data` tetap ada walau kontainer backend dihapus.
#
#   powershell -ExecutionPolicy Bypass -File scripts\data-immunity-test.ps1

$ErrorActionPreference = "Stop"
$api = "http://localhost:8000"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "`n[1] Tambah antrean baru" -ForegroundColor Cyan
$body = @{ name = "Demo Data Immunity"; nim = "1301229999"; service = "umum" } | ConvertTo-Json
$res = Invoke-RestMethod -Method Post -Uri "$api/queue" -ContentType "application/json" -Body $body
Write-Host ("    Tiket: {0}" -f $res.data.ticket)

Write-Host "`n[2] Data SEBELUM kontainer dihapus" -ForegroundColor Cyan
$before = Invoke-RestMethod "$api/queue"
$before.data | Format-Table ticket, name, service_label -AutoSize

Write-Host "[3] docker rm -f queue-backend  (kontainer dihancurkan)" -ForegroundColor Yellow
docker rm -f queue-backend | Out-Null
docker ps -a --filter name=queue-backend --format "    sisa kontainer: {{.Names}}"

Write-Host "`n[4] Isi Named Volume queue-db-data" -ForegroundColor Cyan
docker run --rm -v queue-db-data:/data alpine:3.20 cat /data/queue.json

Write-Host "`n[5] Buat ulang kontainer backend" -ForegroundColor Cyan
docker compose up -d backend | Out-Null
for ($i = 0; $i -lt 20; $i++) {
    try { Invoke-RestMethod "$api/health" | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}

Write-Host "`n[6] Data SESUDAH kontainer dibuat ulang" -ForegroundColor Cyan
$after = Invoke-RestMethod "$api/queue"
$after.data | Format-Table ticket, name, service_label -AutoSize

if ($after.count -eq $before.count) {
    Write-Host "HASIL: Data tetap utuh ($($after.count) antrean). Named Volume terbukti menjaga data." -ForegroundColor Green
} else {
    Write-Host "HASIL: Jumlah data berbeda ($($before.count) -> $($after.count))" -ForegroundColor Red
}
