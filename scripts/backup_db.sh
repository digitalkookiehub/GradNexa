#!/usr/bin/env bash
# Usage: scripts/backup_db.sh [output_dir]   (run from the repo root, stack up)
# Writes a compressed custom-format pg_dump of the compose database. Keep copies off this machine.
set -euo pipefail
OUT="${1:-backups}"
mkdir -p "$OUT"
FILE="$OUT/gradnexa-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE"
test -s "$FILE" || { echo "backup is empty" >&2; rm -f "$FILE"; exit 1; }
echo "wrote $FILE ($(wc -c < "$FILE") bytes)"
