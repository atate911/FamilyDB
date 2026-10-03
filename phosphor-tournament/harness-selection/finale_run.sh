#!/bin/sh
# Render every page, desktop and phone, of each finalist: finale-shots/<id>/<page>--<desktop|phone>.png
H=$(cd "$(dirname "$0")" && pwd); cd "$H"; ROOT=$(cd ../.. && pwd)
for ID in "$@"; do
  V="$H/variants/$ID"
  PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
  ( . "$ROOT/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$ROOT/serve_variant.py" "$V/templates" "$PORT" ) > "out/$ID/variant.log" 2>&1 &
  SPID=$!
  i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { echo "no server for $ID"; kill $SPID; exit 1; }; sleep 0.5; done
  FAMILYDB_BASE="http://127.0.0.1:$PORT" STATIC_OVERRIDE="$V/static" NODE_PATH=$(npm root -g) timeout 600 node finale_render.js "out/$ID" "$H/finale-shots/$ID"
  kill $SPID 2>/dev/null
done
