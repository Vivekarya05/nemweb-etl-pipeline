#!/bin/zsh

PORT_PID="$(lsof -tiTCP:5000 -sTCP:LISTEN 2>/dev/null || true)"

if [ -n "$PORT_PID" ]; then
  kill "$PORT_PID"
fi
