@echo off
:: Helper untuk mengatur IP Master Server dari Laptop 2 (Teman)
if "%1"=="" (
    echo Penggunaan: set_master [IP_SERVER]
    echo Contoh   : set_master 192.168.1.15
    exit /b 1
)

echo %1> master_ip.txt
echo Berhasil! Target Master IP disetel ke: %1
echo Sekarang teman Anda cukup menjalankan:
echo   run_client jadwal
echo   run_client pesan J1 Teman A1
