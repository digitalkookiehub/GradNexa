#!/usr/bin/env bash
# Usage: scripts/restore_db.sh backups/gradnexa-XXXX.dump
# DESTRUCTIVE: replaces the contents of the compose database with the dump. Stop the backend first:
#   docker compose stop backend frontend
set -euo pipefail
FILE="${1:?usage: restore_db.sh <dump file>}"
test -s "$FILE" || { echo "no such dump: $FILE" >&2; exit 1; }
if [ "${CONFIRM:-}" != "yes" ]; then
  echo "This overwrites the current database. Re-run with CONFIRM=yes to proceed." >&2
  exit 1
fi
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$FILE"
echo "restored $FILE; start the stack again: docker compose up -d"
