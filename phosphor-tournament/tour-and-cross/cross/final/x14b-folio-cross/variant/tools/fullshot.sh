#!/bin/sh
# Full-page shots: fullshot.sh WIDTH /path ...
H=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
X=$H/cross/x14b-b; V=$X/variants/x14b-folio-cross
W=$1; shift
cd $X && python3 theme.py palettes/x14b-folio-cross.json out/x14b-folio-cross/style.css >/dev/null
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$H/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$H/serve_variant.py" "$V/templates" "$PORT" ) > "$V/tools/serve.log" 2>&1 &
SPID=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { kill $SPID; exit 1; }; sleep 0.5; done
mkdir -p $V/tools/crops
cd "$V/tools" && NODE_PATH=$(npm root -g) node full.js "http://127.0.0.1:$PORT" "$X/out/x14b-folio-cross/style.css" crops "$W" "$@"
kill $SPID
