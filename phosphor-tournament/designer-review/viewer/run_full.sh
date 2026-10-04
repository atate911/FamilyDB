#!/bin/sh
# usage: run_full.sh <id> [templates-dir-override]
ID=$1; H=$(cd "$(dirname "$0")" && pwd); S=$(cd "$H/../.." && pwd)
V="$H/variants/$ID"; T="${2:-$V/templates}"
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$S/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$S/serve_variant.py" "$T" "$PORT" ) > "$H/out/$ID/full.log" 2>&1 &
SP=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { echo "$ID: server did not start"; kill $SP; exit 1; }; sleep 0.5; done
cd "$H" && FAMILYDB_BASE="http://127.0.0.1:$PORT" STATIC_OVERRIDE="$V/static" NODE_PATH=$(npm root -g) timeout 600 node render_full.js "out/$ID" && echo "$ID done"
kill $SP 2>/dev/null
