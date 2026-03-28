$pids = Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique
foreach ($p in $pids) {
    Write-Host "Killing PID $p"
    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
}
# Zabit take python procesy ktere drzi port (vcetne rodicovskeho reloaderu)
Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
    $connections = Get-NetTCPConnection -OwningProcess $_.Id -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($connections) {
        Write-Host "Killing python PID $($_.Id)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Milliseconds 500
$remaining = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($remaining) { Write-Host "Stale bezi: $($remaining.OwningProcess -join ', ')" }
else { Write-Host "Port 8000 je volny." }
