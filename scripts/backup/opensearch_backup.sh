#!/usr/bin/env bash
# SCR Platform — OpenSearch/Elasticsearch Snapshot
#
# Required env vars:
#   OPENSEARCH_ENDPOINT  (e.g. https://search-scr-xxx.eu-west-1.es.amazonaws.com)
#   AWS_S3_BACKUP_BUCKET
#   AWS_REGION

set -euo pipefail

: "${OPENSEARCH_ENDPOINT:?OPENSEARCH_ENDPOINT required}"
: "${AWS_S3_BACKUP_BUCKET:?AWS_S3_BACKUP_BUCKET required}"
: "${AWS_REGION:?AWS_REGION required}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_REPO="scr-search-backups"
SNAPSHOT_NAME="backup_${TIMESTAMP}"
KEEP_SNAPSHOTS=8

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "Starting OpenSearch snapshot: ${SNAPSHOT_NAME}"

# Register snapshot repository (idempotent)
curl -sf -X PUT "${OPENSEARCH_ENDPOINT}/_snapshot/${SNAPSHOT_REPO}" \
  -H "Content-Type: application/json" \
  -d "{
    \"type\": \"s3\",
    \"settings\": {
      \"bucket\": \"${AWS_S3_BACKUP_BUCKET}\",
      \"base_path\": \"opensearch\",
      \"region\": \"${AWS_REGION}\",
      \"server_side_encryption\": true,
      \"compress\": true
    }
  }" | python3 -m json.tool || log "Snapshot repo already registered or registration warning"

log "Snapshot repository registered: ${SNAPSHOT_REPO}"

# Create snapshot (async — don't wait_for_completion to avoid timeout)
HTTP_STATUS=$(curl -sf -o /tmp/snap_response.json -w "%{http_code}" \
  -X PUT "${OPENSEARCH_ENDPOINT}/_snapshot/${SNAPSHOT_REPO}/${SNAPSHOT_NAME}" \
  -H "Content-Type: application/json" \
  -d '{"indices":"*","ignore_unavailable":true,"include_global_state":true}')

if [[ "${HTTP_STATUS}" =~ ^2 ]]; then
  log "✅ Snapshot initiated: ${SNAPSHOT_NAME} (HTTP ${HTTP_STATUS})"
else
  log "❌ Snapshot failed with HTTP ${HTTP_STATUS}"
  cat /tmp/snap_response.json
  exit 1
fi

# Prune old snapshots — keep only the last KEEP_SNAPSHOTS
log "Pruning old snapshots (keeping last ${KEEP_SNAPSHOTS})..."
OLD_SNAPSHOTS=$(curl -sf "${OPENSEARCH_ENDPOINT}/_snapshot/${SNAPSHOT_REPO}/_all" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
snapshots = sorted(data.get('snapshots', []), key=lambda x: x.get('start_time_in_millis', 0))
# Print all but the last KEEP_SNAPSHOTS
for s in snapshots[:-${KEEP_SNAPSHOTS}]:
    print(s['snapshot'])
" 2>/dev/null || true)

for SNAP in ${OLD_SNAPSHOTS}; do
  curl -sf -X DELETE "${OPENSEARCH_ENDPOINT}/_snapshot/${SNAPSHOT_REPO}/${SNAP}" > /dev/null && \
    log "Deleted old snapshot: ${SNAP}" || log "Warning: could not delete ${SNAP}"
done

log "OpenSearch snapshot complete ✅"
