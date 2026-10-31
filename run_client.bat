@echo off
:: Wrapper Client Singkat (Windows Batch)
:: Membaca IP dari master_ip.txt, atau default localhost

set MASTER_IP=localhost
if exist master_ip.txt (
    set /p MASTER_IP=<master_ip.txt
)

if "%1"=="" (
    echo Penggunaan: run_client [perintah] [argumen...]
    echo Target server: %MASTER_IP%:50051
    echo.
    echo Contoh:
    echo   run_client jadwal
    echo   run_client peta J1
    echo   run_client pesan J1 Andi A1 A2
    echo   run_client batal J1-0001 Andi
    echo   run_client pantau J1
    exit /b 0
)

python klien_cli.py --host %MASTER_IP%:50051 %*
