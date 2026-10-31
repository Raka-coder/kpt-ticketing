#!/usr/bin/env bash
# Wrapper Client Singkat (Linux/Mac)
MASTER_IP="localhost"
if [ -f "master_ip.txt" ]; then
    MASTER_IP=$(cat master_ip.txt | tr -d '[:space:]')
fi

if [ $# -eq 0 ]; then
    echo "Penggunaan: ./run_client.sh [perintah] [argumen...]"
    echo "Target server: ${MASTER_IP}:50051"
    echo ""
    echo "Contoh:"
    echo "  ./run_client.sh jadwal"
    echo "  ./run_client.sh peta J1"
    echo "  ./run_client.sh pesan J1 Andi A1 A2"
    exit 0
fi

python3 klien_cli.py --host "${MASTER_IP}:50051" "$@"
