#!/usr/bin/env bash
# Start the SDLC360 web app in the background: http://127.0.0.1:${PORT:-8360}/
# Usage: ./start.sh [--open]      (PORT=8361 ./start.sh to use another port)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
PORT="${PORT:-8360}"
URL="http://127.0.0.1:$PORT/"
LOG="$ROOT/.cache/server.log"

for py in .venv/Scripts/python.exe .venv/bin/python python3 python; do
    if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
        PY="$py"; break
    fi
done
[[ -n "${PY:-}" ]] || { echo "Python 3.12+ not found."; exit 1; }

if curl -sf "${URL}api/projects" >/dev/null 2>&1; then
    echo "SDLC360 already running at $URL"
    exit 0
fi

mkdir -p .cache
nohup "$PY" -u sdlc.py serve --port "$PORT" > "$LOG" 2>&1 < /dev/null &
pid=$!
for ((i = 0; i < 100; i++)); do
    if curl -sf "${URL}api/projects" >/dev/null 2>&1; then
        echo "SDLC360 running at $URL"
        echo "Log:  $LOG"
        echo "Stop: ./stop.sh"
        [[ " $* " == *" --open "* ]] && "$PY" -m webbrowser "$URL" >/dev/null 2>&1 || true
        exit 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
        cat "$LOG"
        echo "SDLC360 did not start. If port $PORT is busy: PORT=8361 ./start.sh"
        exit 1
    fi
    sleep 0.1
done
echo "SDLC360 is still starting; see $LOG"
exit 1
