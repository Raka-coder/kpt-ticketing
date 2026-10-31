# Wrapper Client Singkat (PowerShell)
# Membaca IP dari master_ip.txt, atau default localhost

$MasterIp = "localhost"
if (Test-Path "master_ip.txt") {
    $MasterIp = (Get-Content "master_ip.txt" -Raw).Trim()
}

if ($args.Count -eq 0) {
    Write-Host "Penggunaan: .\run_client.ps1 [perintah] [argumen...]" -ForegroundColor Cyan
    Write-Host "Target server: ${MasterIp}:50051" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Contoh:"
    Write-Host "  .\run_client.ps1 jadwal"
    Write-Host "  .\run_client.ps1 peta J1"
    Write-Host "  .\run_client.ps1 pesan J1 Andi A1 A2"
    Write-Host "  .\run_client.ps1 batal J1-0001 Andi"
    Write-Host "  .\run_client.ps1 pantau J1"
    exit 0
}

python klien_cli.py --host "${MasterIp}:50051" @args
