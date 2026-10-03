#!/bin/sh
# Usage: tools/tgt.sh WIDTH /path ...   targets under 44px (after ./check.sh has built the style)
H=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
T=$H/tour/t1-b; V=$T/variants/t1-switchboard-graft
W=$1; shift
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$H/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$H/serve_variant.py" "$V/templates" "$PORT" ) > "$V/tools/serve.log" 2>&1 &
SPID=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { kill $SPID; exit 1; }; sleep 0.5; done
cd "$V/tools" && NODE_PATH=$(npm root -g) node targets.js "http://127.0.0.1:$PORT" "$T/out/t1-switchboard-graft/style.css" "$W" "$@"
kill $SPID
