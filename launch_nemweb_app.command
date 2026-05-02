#!/bin/zsh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use the project virtual environment if it exists.
if [ -f ".venv/bin/activate" ]; then
  source ".venv/bin/activate"
fi

# Start the Flask app in the background only if it is not already running.
if ! lsof -nP -iTCP:5000 -sTCP:LISTEN >/dev/null 2>&1; then
  nohup python app.py > "$SCRIPT_DIR/logs/web_app_stdout.log" 2>&1 &
  sleep 3
fi

# Open the dashboard in the default browser.
open "http://127.0.0.1:5000"
