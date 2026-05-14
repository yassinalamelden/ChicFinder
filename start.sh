#!/bin/sh
# Railway injects $PORT at runtime. Fall back to 8000 for local dev.
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
