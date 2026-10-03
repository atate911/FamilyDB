#!/bin/sh
# One palette end to end: themed stylesheet, screenshots of the real pages, the measures.
# Usage: ./check.sh palettes/NN-name.json              all pages
#        ./check.sh palettes/NN-name.json home ideas   only these pages (quicker while iterating)
#        ./check.sh palettes/NN-name.json --no-render
# A palette may carry its own markup in variants/<id>/templates (and pictures or icons in
# variants/<id>/static): it is checked (lint_variant.py), then served for this render only by its
# own server on a free port (serve_variant.py).
set -e
H=$(cd "$(dirname "$0")" && pwd)
cd "$H"
ROOT="$H"; while [ ! -f "$ROOT/serve_variant.py" ] && [ "$ROOT" != "/" ]; do ROOT=$(dirname "$ROOT"); done
P="$1"; shift
ID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['id'])" "$P")
python3 theme.py "$P" "out/$ID/style.css"
if [ "$1" != "--no-render" ]; then
  V="$H/variants/$ID"
  BASE_URL=http://127.0.0.1:8099
  SPID=""
  if [ -d "$V" ]; then
    python3 "$ROOT/lint_variant.py" "$V"
  fi
  if [ -d "$V/templates" ]; then
    PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1])")
    ( . "$ROOT/demo.env"; cd /home/user/FamilyDB && exec .venv/bin/python "$ROOT/serve_variant.py" "$V/templates" "$PORT" ) > "out/$ID/variant.log" 2>&1 &
    SPID=$!
    i=0; until curl -s -o /dev/null "http://127.0.0.1:$PORT/login"; do i=$((i+1)); [ $i -gt 60 ] && { echo "variant server did not start: see out/$ID/variant.log"; kill $SPID 2>/dev/null; exit 1; }; sleep 0.5; done
    BASE_URL="http://127.0.0.1:$PORT"
  fi
  STATUS=0
  FAMILYDB_BASE="$BASE_URL" STATIC_OVERRIDE="$V/static" NODE_PATH=$(npm root -g) timeout 300 node render.js "out/$ID" "$@" >/dev/null || STATUS=$?
  [ -n "$SPID" ] && kill "$SPID" 2>/dev/null
  [ "$STATUS" = 0 ] || { echo "render failed ($STATUS)"; exit 1; }
fi
./venv/bin/python metrics.py "$P"
