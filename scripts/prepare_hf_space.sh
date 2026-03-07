#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
OUT_DIR="${1:-$ROOT_DIR/.build/hf-space}"
SPACE_TITLE="${HF_SPACE_TITLE:-Face Attendance Backend}"
SPACE_COLOR_FROM="${HF_SPACE_COLOR_FROM:-blue}"
SPACE_COLOR_TO="${HF_SPACE_COLOR_TO:-green}"

mkdir -p "$OUT_DIR"

rm -rf "$OUT_DIR/app" "$OUT_DIR/models"

cp -R "$BACKEND_DIR/app" "$OUT_DIR/app"
cp -R "$BACKEND_DIR/models" "$OUT_DIR/models"
cp "$BACKEND_DIR/requirements.txt" "$OUT_DIR/requirements.txt"
cp "$BACKEND_DIR/Dockerfile" "$OUT_DIR/Dockerfile"

cat > "$OUT_DIR/README.md" <<EOF
---
title: $SPACE_TITLE
colorFrom: $SPACE_COLOR_FROM
colorTo: $SPACE_COLOR_TO
sdk: docker
app_port: 8000
---

FastAPI backend for the face attendance system.
EOF

echo "Prepared Hugging Face Space files in: $OUT_DIR"
