#!/bin/sh
# ./variants/r8-idea-2/probe.sh URL [WIDTH] [EXPR]: run probe.js against this palette's own markup.
H=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
V=$H/rounds/r10/variants/r10-mut-4
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$H/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$H/serve_variant.py" "$V/templates" "$PORT" ) > /dev/null 2>&1 &
SPID=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { kill $SPID; exit 1; }; sleep 0.5; done
cd $H/rounds/r10 && FAMILYDB_BASE="http://127.0.0.1:$PORT" NODE_PATH=$(npm root -g) node $V/probe.js "$@"
kill $SPID
