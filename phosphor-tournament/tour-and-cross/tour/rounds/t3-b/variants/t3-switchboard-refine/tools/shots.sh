#!/bin/sh
# Usage: tools/shots.sh "w|route|name[|full][|hover][|js]" ...   (rebuilds style.css first)
H=/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness
T=$H/tour/t3-b; V=$T/variants/t3-switchboard-refine
sh "$V/tools/build.sh" >/dev/null
(cd "$T" && python3 theme.py palettes/t3-switchboard-refine.json out/t3-switchboard-refine/style.css) >/dev/null
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
( . "$H/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$H/serve_variant.py" "$V/templates" "$PORT" ) > "$V/tools/serve.log" 2>&1 &
SPID=$!
i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { kill $SPID; exit 1; }; sleep 0.5; done
cd "$V/tools" && NODE_PATH=$(npm root -g) node shots.js "http://127.0.0.1:$PORT" "$T/out/t3-switchboard-refine/style.css" /tmp/claude-0/-home-user-FamilyDB/120fcf6f-20be-59ef-8e10-e5252598c703/scratchpad/shots "$@"
kill $SPID
