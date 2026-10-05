#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================================="
echo "Starting Hearth - Offline Live Captions & Speech Translation"
echo "========================================================="

if [ -f "venv/bin/python" ]; then
    PYTHON_EXE="venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXE="python3"
else
    PYTHON_EXE="python"
fi

"$PYTHON_EXE" scripts/launch_hearth.py "$@"
