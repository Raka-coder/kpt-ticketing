"""Generate gRPC stubs from proto/bioskop.proto and proto/admin.proto into project root."""
import subprocess
import sys

cmd = [sys.executable, "-m", "grpc_tools.protoc", "-I", "proto",
       "--python_out=.", "--grpc_python_out=.", "proto/bioskop.proto", "proto/admin.proto"]
raise SystemExit(subprocess.call(cmd))

