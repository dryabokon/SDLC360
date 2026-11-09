#!/usr/bin/env bash
# Stop the SDLC360 web app started by start.sh. A scan in progress is interrupted; finished runs stay in runs/.
set -euo pipefail
PORT="${PORT:-8360}"
URL="http://127.0.0.1:$PORT/"

# Under WSL the server may run on the Windows side (see start.sh); then only Windows curl.exe reaches it.
CURL=curl
if ! curl -sf "${URL}api/projects" >/dev/null 2>&1; then
    if command -v curl.exe >/dev/null 2>&1 && curl.exe -sf "${URL}api/projects" >/dev/null 2>&1; then
        CURL=curl.exe
    else
        echo "SDLC360 is not running on port $PORT."
        exit 0
    fi
fi
"$CURL" -sf -X POST -H "Origin: http://127.0.0.1:$PORT" "${URL}api/shutdown" >/dev/null
for ((i = 0; i < 50; i++)); do
    if ! "$CURL" -sf "${URL}api/projects" >/dev/null 2>&1; then
        echo "SDLC360 stopped."
        exit 0
    fi
    sleep 0.1
done
echo "SDLC360 did not stop within 5 s."
exit 1
