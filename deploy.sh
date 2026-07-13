#!/usr/bin/env bash
# One-shot rsync deploy of the KTTV scraper to a remote host.
#
# Usage:
#   ./deploy.sh user@host:/target/path         # DRY-RUN (preview only, copies nothing)
#   ./deploy.sh user@host:/target/path --go     # actually copy
#
# Excludes local configuration, private notes, caches, and the remote's dedup
# state file so a deployment does not copy or overwrite private operational
# data.
set -euo pipefail

DEST="${1:-}"
if [ -z "$DEST" ]; then
    echo "usage: ./deploy.sh user@host:/target/path [--go]" >&2
    exit 2
fi

# Trailing slash on SRC => copy the *contents* into DEST (not a nested folder).
SRC="$(cd "$(dirname "$0")" && pwd)/"

DRY="--dry-run"
[ "${2:-}" = "--go" ] && DRY=""

echo ">>> rsync ${DRY:-(LIVE)}  $SRC  ->  $DEST"
rsync -avz $DRY \
    --exclude='.git/' \
    --exclude='_to_remove/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='kttv_state.json' \
    --exclude='*.state.json' \
    --exclude='sites.json' \
    --exclude='sites.local.json' \
    --exclude='private/' \
    --exclude='*.private.json' \
    --exclude='*.private.md' \
    --exclude='sites.local.*' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='REVERSE_ENGINEERING.md' \
    --exclude='操作手冊.md' \
    --exclude='部署手冊.md' \
    --exclude='.venv/' \
    --exclude='uv.lock' \
    --exclude='*.tmp' \
    --exclude='*.log' \
    --exclude='logs/' \
    --exclude='.DS_Store' \
    "$SRC" "$DEST"

if [ -n "$DRY" ]; then
    echo ""
    echo ">>> DRY-RUN only — nothing was copied. Re-run with --go to deploy for real."
fi
