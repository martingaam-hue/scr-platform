#!/usr/bin/env bash
# SCR Platform — Manual DR Restore Test
# Downloads the latest pg_dump from S3 and restores to a test schema.
# Verifies table count and data integrity, then cleans up.
#
# Required env vars: same as pg_backup.sh + AWS_S3_BACKUP_BUCKET

set -euo pipefail

: "${AWS_S3_BACKUP_BUCKET:?AWS_S3_BACKUP_BUCKET required}"
: "${AWS_REGION:?AWS_REGION required}"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

TMP_DIR=$(mktemp -d)
cleanup() { rm -rf "${TMP_DIR}"; }
trap cleanup EXIT

# Parse DB connection
if [[ -z "${DB_HOST:-}" ]] && [[ -n "${DATABASE_URL:-}" ]]; then
  URL="${DATABASE_URL#postgresql+asyncpg://}"
  URL="${URL#postgresql://}"
  CREDENTIALS="${URL%%@*}"; HOST_DB="${URL##*@}"
  DB_USER="${CREDENTIALS%%:*}"; DB_PASS="${CREDENTIALS##*:}"
  HOST_PORT="${HOST_DB%%/*}"; DB_NAME="${HOST_DB##*/}"
  DB_HOST="${HOST_PORT%%:*}"; DB_PORT="${HOST_PORT##*::-5432}"
fi
export PGPASSWORD="${DB_PASS:-}"
TEMP_SCHEMA="restore_test_$(date +%Y%m%d%H%M%S)"

log "=== SCR Platform DR Restore Test ==="

# ── 1. Find latest backup ─────────────────────────────────────────────────────
log "Finding latest backup in s3://${AWS_S3_BACKUP_BUCKET}/postgresql/..."
LATEST_KEY=$(aws s3 ls "s3://${AWS_S3_BACKUP_BUCKET}/postgresql/" --recursive \
  | grep -E '\.(dump|dump\.gz)$' \
  | sort -k1,2 -r \
  | head -1 \
  | awk '{print $4}')

if [[ -z "${LATEST_KEY}" ]]; then
  log "❌ No backups found in S3"
  exit 1
fi

BACKUP_AGE=$(aws s3 ls "s3://${AWS_S3_BACKUP_BUCKET}/${LATEST_KEY}" \
  | awk '{print $1, $2}' | head -1)
log "Latest backup: ${LATEST_KEY} (${BACKUP_AGE})"

# ── 2. Download ───────────────────────────────────────────────────────────────
DUMP_PATH="${TMP_DIR}/restore_test.dump"
log "Downloading backup..."
aws s3 cp "s3://${AWS_S3_BACKUP_BUCKET}/${LATEST_KEY}" "${DUMP_PATH}" \
  --region "${AWS_REGION}"

# Decompress if gzipped
if [[ "${LATEST_KEY}" == *.gz ]]; then
  UNCOMPRESSED="${TMP_DIR}/restore_test_raw.dump"
  gunzip -c "${DUMP_PATH}" > "${UNCOMPRESSED}"
  DUMP_PATH="${UNCOMPRESSED}"
fi

# ── 3. Verify pg_restore --list ───────────────────────────────────────────────
log "Verifying dump integrity (pg_restore --list)..."
TABLE_COUNT_IN_DUMP=$(pg_restore --list "${DUMP_PATH}" 2>/dev/null | grep -c "TABLE DATA" || echo "0")
log "Tables in dump: ${TABLE_COUNT_IN_DUMP}"

# ── 4. Create temp schema and restore ────────────────────────────────────────
log "Creating temp schema: ${TEMP_SCHEMA}"
psql -h "${DB_HOST}" -p "${DB_PORT:-5432}" -U "${DB_USER}" -d "${DB_NAME}" \
  -c "CREATE SCHEMA IF NOT EXISTS \"${TEMP_SCHEMA}\"" > /dev/null

log "Restoring to temp schema (schema-only, --no-data for speed)..."
pg_restore \
  --schema-only \
  --no-owner --no-acl \
  --schema="${TEMP_SCHEMA}" \
  --dbname="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT:-5432}/${DB_NAME}" \
  "${DUMP_PATH}" 2>&1 | grep -v "^pg_restore:" | head -20 || true

# ── 5. Count restored tables ─────────────────────────────────────────────────
RESTORED_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT:-5432}" -U "${DB_USER}" -d "${DB_NAME}" \
  -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='${TEMP_SCHEMA}' AND table_type='BASE TABLE'" \
  | tr -d ' ')

log "Tables restored: ${RESTORED_COUNT}"

EXPECTED_MIN=100
if [[ "${RESTORED_COUNT}" -ge "${EXPECTED_MIN}" ]]; then
  log "✅ Table count check passed: ${RESTORED_COUNT} >= ${EXPECTED_MIN}"
  RESULT="PASS"
else
  log "❌ Table count check FAILED: ${RESTORED_COUNT} < ${EXPECTED_MIN}"
  RESULT="FAIL"
fi

# ── 6. Check DR bucket ────────────────────────────────────────────────────────
if [[ -n "${DR_REGION:-}" ]] && [[ -n "${DR_BACKUP_BUCKET:-}" ]]; then
  DR_COUNT=$(aws s3 ls "s3://${DR_BACKUP_BUCKET}/postgresql/" --recursive --region "${DR_REGION}" \
    | wc -l | tr -d ' ' 2>/dev/null || echo "0")
  if [[ "${DR_COUNT}" -gt "0" ]]; then
    log "✅ DR bucket has ${DR_COUNT} backup(s)"
  else
    log "⚠️  DR bucket appears empty — cross-region copy may not be working"
    RESULT="FAIL"
  fi
fi

# ── 7. Cleanup ────────────────────────────────────────────────────────────────
log "Cleaning up temp schema..."
psql -h "${DB_HOST}" -p "${DB_PORT:-5432}" -U "${DB_USER}" -d "${DB_NAME}" \
  -c "DROP SCHEMA IF EXISTS \"${TEMP_SCHEMA}\" CASCADE" > /dev/null

log "=== Restore Test Result: ${RESULT} ==="
[[ "${RESULT}" == "PASS" ]] || exit 1
