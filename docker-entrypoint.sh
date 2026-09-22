#!/usr/bin/env bash
set -u

open_webui_pid=""

stop_open_webui() {
    if [[ -n "$open_webui_pid" ]] \
        && kill -0 "$open_webui_pid" 2>/dev/null; then
        kill -TERM "$open_webui_pid" 2>/dev/null || true
    fi
}

trap stop_open_webui SIGTERM SIGINT

bash /app/backend/start.sh &
open_webui_pid=$!

if python /opt/garmin-trainer/bootstrap_openwebui.py; then
    echo "Bootstrap Open WebUI zakończony."
else
    bootstrap_status=$?
    echo "Bootstrap Open WebUI nie powiódł się (status ${bootstrap_status})." >&2
    stop_open_webui
    wait "$open_webui_pid" 2>/dev/null || true
    exit "$bootstrap_status"
fi

wait "$open_webui_pid"
open_webui_status=$?

exit "$open_webui_status"
