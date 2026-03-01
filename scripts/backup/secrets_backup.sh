#!/usr/bin/env bash
# SCR Platform — Secrets & Config Inventory Backup
# Exports secret NAMES (NOT values) and DNS records to S3 as audit record.
#
# Required env vars:
#   AWS_REGION
#   AWS_S3_BACKUP_BUCKET

set -euo pipefail

: "${AWS_REGION:?AWS_REGION required}"
: "${AWS_S3_BACKUP_BUCKET:?AWS_S3_BACKUP_BUCKET required}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MONTH=$(date +%Y%m)
TMP_DIR=$(mktemp -d)

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
cleanup() { rm -rf "${TMP_DIR}"; }
trap cleanup EXIT

log "Starting secrets inventory backup..."

# ── Secrets Manager inventory (names only, NOT values) ────────────────────────
SECRETS_FILE="${TMP_DIR}/secrets_inventory.json"
aws secretsmanager list-secrets \
  --region "${AWS_REGION}" \
  --query 'SecretList[*].{Name:Name,ARN:ARN,LastRotated:LastRotatedDate,Created:CreatedDate}' \
  --output json > "${SECRETS_FILE}" 2>/dev/null || echo '[]' > "${SECRETS_FILE}"

SECRET_COUNT=$(python3 -c "import json; data=json.load(open('${SECRETS_FILE}')); print(len(data))" 2>/dev/null || echo "unknown")
log "Secrets inventoried: ${SECRET_COUNT}"

# Wrap with metadata
python3 - << PYEOF
import json, datetime
with open('${SECRETS_FILE}') as f:
    secrets = json.load(f)
report = {
    "timestamp": "${TIMESTAMP}",
    "region": "${AWS_REGION}",
    "secret_count": len(secrets),
    "secrets": secrets,
    "note": "SECRET VALUES ARE NOT STORED. This file contains only names and ARNs for inventory purposes."
}
with open('${SECRETS_FILE}', 'w') as f:
    json.dump(report, f, indent=2, default=str)
PYEOF

# ── Route53 DNS records backup ────────────────────────────────────────────────
DNS_FILE="${TMP_DIR}/dns_records.json"
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='scr-platform.com.'].Id" \
  --output text 2>/dev/null | sed 's|/hostedzone/||' || echo "")

if [[ -n "${HOSTED_ZONE_ID}" ]]; then
  aws route53 list-resource-record-sets \
    --hosted-zone-id "${HOSTED_ZONE_ID}" \
    --output json > "${DNS_FILE}" 2>/dev/null || echo '{}' > "${DNS_FILE}"
  log "DNS records exported for zone: ${HOSTED_ZONE_ID}"
else
  echo '{"note": "No hosted zone found for scr-platform.com"}' > "${DNS_FILE}"
  log "No Route53 hosted zone found"
fi

# ── ECS service configuration inventory ──────────────────────────────────────
ECS_FILE="${TMP_DIR}/ecs_services.json"
CLUSTER="scr-${APP_ENV:-production}"
aws ecs list-services --cluster "${CLUSTER}" --region "${AWS_REGION}" \
  --output json > "${ECS_FILE}" 2>/dev/null || echo '{}' > "${ECS_FILE}"

# ── Upload all to S3 ─────────────────────────────────────────────────────────
for FILE in "${SECRETS_FILE}" "${DNS_FILE}" "${ECS_FILE}"; do
  BASENAME=$(basename "${FILE}")
  S3_KEY="config-inventory/${MONTH}/${TIMESTAMP}_${BASENAME}"
  aws s3 cp "${FILE}" "s3://${AWS_S3_BACKUP_BUCKET}/${S3_KEY}" \
    --region "${AWS_REGION}" \
    --content-type application/json \
    --sse AES256
  log "Uploaded: s3://${AWS_S3_BACKUP_BUCKET}/${S3_KEY}"
done

log "Secrets & config inventory complete ✅"
