#!/usr/bin/env bash
# SCR Platform — PostgreSQL Logical Backup
# Runs from within ECS task or locally for manual backups.
# Called by the nightly_backup Celery task OR directly as a standalone script.
#
# Required env vars:
#   DATABASE_URL or DB_HOST/DB_PORT/DB_USER/DB_PASS/DB_NAME
#   AWS_S3_BACKUP_BUCKET  (e.g. scr-production-backups)
#   AWS_REGION            (e.g. eu-west-1)
#   DR_REGION             (e.g. eu-central-1)
#   DR_BACKUP_BUCKET      (e.g. scr-backups-eu-central-1)
#   KMS_KEY_ID            (optional, for SSE-KMS)

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MONTH=$(date +%Y%m)
BACKUP_FILE="scr_production_${TIMESTAMP}.dump"
TMP_DIR=$(mktemp -d)
BACKUP_PATH="${TMP_DIR}/${BACKUP_FILE}"

# Retention tiers
KEEP_DAILY=30    # days
KEEP_WEEKLY=12   # weeks (Sundays)
KEEP_MONTHLY=12  # months (1st of month)

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a /var/log/scr_backup.log 2>/dev/null || echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

cleanup() { rm -rf "${TMP_DIR}"; }
trap cleanup EXIT

# ── Parse DATABASE_URL if individual vars not set ────────────────────────────
if [[ -z "${DB_HOST:-}" ]] && [[ -n "${DATABASE_URL:-}" ]]; then
  URL="${DATABASE_URL}"
  URL="${URL#postgresql+asyncpg://}"
  URL="${URL#postgresql://}"
  CREDENTIALS="${URL%%@*}"
  HOST_DB="${URL##*@}"
  DB_USER="${CREDENTIALS%%:*}"
  DB_PASS="${CREDENTIALS##*:}"
  HOST_PORT="${HOST_DB%%/*}"
  DB_NAME="${HOST_DB##*/}"
  DB_HOST="${HOST_PORT%%:*}"
  DB_PORT="${HOST_PORT##*:}"
  DB_PORT="${DB_PORT:-5432}"
fi

: "${DB_HOST:?DB_HOST or DATABASE_URL required}"
: "${DB_USER:?DB_USER required}"
: "${DB_NAME:?DB_NAME required}"
: "${AWS_S3_BACKUP_BUCKET:?AWS_S3_BACKUP_BUCKET required}"
: "${AWS_REGION:?AWS_REGION required}"

export PGPASSWORD="${DB_PASS:-}"

S3_KEY="postgresql/${MONTH}/${BACKUP_FILE}"

log "Starting PostgreSQL backup: ${DB_NAME}@${DB_HOST}"

# ── pg_dump ──────────────────────────────────────────────────────────────────
pg_dump \
  --host="${DB_HOST}" \
  --port="${DB_PORT:-5432}" \
  --username="${DB_USER}" \
  --dbname="${DB_NAME}" \
  --no-password \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-acl \
  --file="${BACKUP_PATH}"

BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)
log "Dump complete: ${BACKUP_FILE} (${BACKUP_SIZE})"

# ── Upload to primary S3 ─────────────────────────────────────────────────────
SSE_ARGS=()
if [[ -n "${KMS_KEY_ID:-}" ]]; then
  SSE_ARGS=(--sse aws:kms --sse-kms-key-id "${KMS_KEY_ID}")
fi

aws s3 cp "${BACKUP_PATH}" "s3://${AWS_S3_BACKUP_BUCKET}/${S3_KEY}" \
  --storage-class STANDARD_IA \
  --region "${AWS_REGION}" \
  "${SSE_ARGS[@]}" \
  --metadata "timestamp=${TIMESTAMP},db=${DB_NAME}"

log "Uploaded to s3://${AWS_S3_BACKUP_BUCKET}/${S3_KEY}"

# ── Upload to DR region ──────────────────────────────────────────────────────
if [[ -n "${DR_REGION:-}" ]] && [[ -n "${DR_BACKUP_BUCKET:-}" ]]; then
  aws s3 cp "${BACKUP_PATH}" "s3://${DR_BACKUP_BUCKET}/${S3_KEY}" \
    --storage-class STANDARD_IA \
    --region "${DR_REGION}" \
    "${SSE_ARGS[@]}"
  log "DR copy uploaded to s3://${DR_BACKUP_BUCKET}/${S3_KEY} (${DR_REGION})"
else
  log "DR copy skipped: DR_REGION or DR_BACKUP_BUCKET not set"
fi

# ── Verify backup (pg_restore --list) ────────────────────────────────────────
log "Verifying backup integrity..."
VERIFY_PATH="${TMP_DIR}/verify.dump"
aws s3 cp "s3://${AWS_S3_BACKUP_BUCKET}/${S3_KEY}" "${VERIFY_PATH}" --quiet

if pg_restore --list "${VERIFY_PATH}" > /dev/null 2>&1; then
  log "✅ Backup verified successfully"
  VERIFIED=true
else
  log "❌ BACKUP VERIFICATION FAILED — pg_restore --list returned non-zero"
  VERIFIED=false
fi

# ── Table count audit ────────────────────────────────────────────────────────
TABLE_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT:-5432}" -U "${DB_USER}" -d "${DB_NAME}" \
  -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'" \
  2>/dev/null | tr -d ' ' || echo "unknown")
log "Table count: ${TABLE_COUNT}"

# ── Emit metadata JSON ────────────────────────────────────────────────────────
cat << EOF
{
  "timestamp": "${TIMESTAMP}",
  "file": "${BACKUP_FILE}",
  "size": "${BACKUP_SIZE}",
  "s3_primary": "s3://${AWS_S3_BACKUP_BUCKET}/${S3_KEY}",
  "s3_dr": "${DR_BACKUP_BUCKET:-none}",
  "verified": ${VERIFIED},
  "table_count": "${TABLE_COUNT}"
}
EOF

# ── Tiered retention cleanup ─────────────────────────────────────────────────
log "Applying tiered retention policy..."

CUTOFF_DAILY=$(date -d "-${KEEP_DAILY} days" +%Y-%m-%d 2>/dev/null || date -v"-${KEEP_DAILY}d" +%Y-%m-%d)
CUTOFF_WEEKLY=$(date -d "-${KEEP_WEEKLY} weeks" +%Y-%m-%d 2>/dev/null || date -v"-${KEEP_WEEKLY}w" +%Y-%m-%d)
CUTOFF_MONTHLY=$(date -d "-${KEEP_MONTHLY} months" +%Y-%m-%d 2>/dev/null || date -v"-${KEEP_MONTHLY}m" +%Y-%m-%d)

aws s3 ls "s3://${AWS_S3_BACKUP_BUCKET}/postgresql/" --recursive | awk '{print $1, $4}' | while read -r FILE_DATE S3_OBJ_KEY; do
  # Skip if within daily retention
  if [[ "${FILE_DATE}" > "${CUTOFF_DAILY}" ]]; then
    continue
  fi
  # Keep Sundays within weekly retention
  DOW=$(date -d "${FILE_DATE}" +%u 2>/dev/null || date -j -f "%Y-%m-%d" "${FILE_DATE}" +%u 2>/dev/null || echo "0")
  if [[ "${DOW}" == "7" ]] && [[ "${FILE_DATE}" > "${CUTOFF_WEEKLY}" ]]; then
    continue
  fi
  # Keep 1st of month within monthly retention
  DOM=$(date -d "${FILE_DATE}" +%d 2>/dev/null || date -j -f "%Y-%m-%d" "${FILE_DATE}" +%d 2>/dev/null || echo "00")
  if [[ "${DOM}" == "01" ]] && [[ "${FILE_DATE}" > "${CUTOFF_MONTHLY}" ]]; then
    continue
  fi
  # Delete
  aws s3 rm "s3://${AWS_S3_BACKUP_BUCKET}/${S3_OBJ_KEY}" --region "${AWS_REGION}" 2>/dev/null && \
    log "Deleted old backup: ${S3_OBJ_KEY}" || true
done

log "Backup pipeline complete ✅"
