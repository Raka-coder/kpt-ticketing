#!/usr/bin/env sh
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/bioskop.proto && echo "Stub dibuat: bioskop_pb2.py, bioskop_pb2_grpc.py"
