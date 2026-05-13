#!/bin/bash
set -e
echo "PORT environment variable: ${PORT:-8000}"
echo "Starting uvicorn with args: --host 0.0.0.0 --port ${PORT:-8000}"
exec python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
