#!/bin/sh
# probe.sh spec.json : build css, serve my templates on a free port, run probe.js
set -e
R=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/rounds/r9
ROOT=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
V=$R/variants/r9-idea-4
cd $R
python3 $V/src/build.py >/dev/null
python3 theme.py palettes/r9-idea-4.json out/r9-idea-4/style.css >/dev/null
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$ROOT/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$ROOT/serve_variant.py" "$V/templates" "$PORT" ) > /dev/null 2>&1 &
SPID=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { kill $SPID; exit 1; }; sleep 0.5; done
NODE_PATH=$(npm root -g) node $V/src/probe.js "http://127.0.0.1:$PORT" out/r9-idea-4/style.css $V/src/shots "$1" || true
kill $SPID 2>/dev/null
