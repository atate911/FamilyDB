#!/bin/sh
# Usage: shoot.sh OUTDIR /status@status /@home ...   (rebuilds the palette css first)
H=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
R=$H/rounds/r12
V=$R/variants/r12-mut-2
python3 $V/build.py >/dev/null && (cd $R && python3 theme.py palettes/r12-mut-2.json out/r12-mut-2/style.css) || exit 1
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$H/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$H/serve_variant.py" "$V/templates" "$PORT" ) > /tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/rounds/r12/variants/r12-mut-2/tools/serve.log 2>&1 &
SPID=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { kill $SPID; echo "server failed"; cat /tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/rounds/r12/variants/r12-mut-2/tools/serve.log | tail; exit 1; }; sleep 0.5; done
FAMILYDB_BASE="http://127.0.0.1:$PORT" NODE_PATH=$(npm root -g) node /tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/rounds/r12/variants/r12-mut-2/tools/shoot.js "$@"
S=$?
kill $SPID
exit $S
