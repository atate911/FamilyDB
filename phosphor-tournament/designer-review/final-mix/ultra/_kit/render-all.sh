#!/bin/sh
# Usage: ./_kit/render-all.sh . [page ...]     (DARK="home chat" ./_kit/render-all.sh . to add dark-mode shots)
NODE_PATH=$(npm root -g) exec node "$(dirname "$0")/render-all.js" "$@"
