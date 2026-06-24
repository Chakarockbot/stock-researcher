#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
  echo "Python 3 not found. Install it and try again."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "First run: creating virtual environment..."
  python3 -m venv .venv
  echo "Installing dependencies..."
  .venv/bin/pip install -r requirements.txt --quiet
  echo
fi

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null || echo "your-local-ip")

echo "Starting StockResearcher..."
echo
echo "Open your browser to:"
echo "  This machine:  http://localhost:8000"
echo "  Local network: http://${LOCAL_IP}:8000"
echo
echo "Press Ctrl+C to stop."
echo
.venv/bin/python app.py
