#!/usr/bin/env sh
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/bioskop.proto proto/admin.proto && echo "Stub berhasil dibuat: bioskop_pb2*.py, admin_pb2*.py"
