#!/bin/sh
# Usage: ./render.sh <your folder>
NODE_PATH=$(npm root -g) exec node "$(dirname "$0")/render.js" "$1"
