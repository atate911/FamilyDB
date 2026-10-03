#!/bin/sh
# Usage: tools/shoot.sh WIDTH /path /path ...   (after ./check.sh has built out/x14b-folio-cross/style.css)
H=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
R=$H/cross/x14b-b; V=$R/variants/x14b-folio-cross
W=$1; shift
mkdir -p "$V/tools/crops"
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$H/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$H/serve_variant.py" "$V/templates" "$PORT" ) > "$V/tools/serve.log" 2>&1 &
SPID=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { kill $SPID; exit 1; }; sleep 0.5; done
cd "$V/tools" && NODE_PATH=$(npm root -g) node full.js "http://127.0.0.1:$PORT" "$R/out/x14b-folio-cross/style.css" "$V/tools/crops" "$W" "$@"
kill $SPID
