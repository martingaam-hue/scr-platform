#!/usr/bin/env bash
# SCR Platform — Rebuild Elasticsearch/OpenSearch Indices from PostgreSQL
# Fallback when snapshot restore isn't available.
# Triggers the SCR API's re-indexing endpoint for all index types.
#
# Required env vars:
#   API_BASE_URL  (e.g. https://api.scr-platform.com)
#   API_ADMIN_JWT (service account JWT with admin scope)
#   OPENSEARCH_ENDPOINT (for direct index deletion)

set -euo pipefail

: "${API_BASE_URL:?API_BASE_URL required}"
: "${API_ADMIN_JWT:?API_ADMIN_JWT required}"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

log "Starting search index rebuild from PostgreSQL..."

AUTH_HEADER="Authorization: Bearer ${API_ADMIN_JWT}"

# ── Delete existing indices (clean slate) ────────────────────────────────────
if [[ -n "${OPENSEARCH_ENDPOINT:-}" ]]; then
  log "Deleting existing indices..."
  for INDEX in scr_projects scr_documents scr_marketplace; do
    curl -sf -X DELETE "${OPENSEARCH_ENDPOINT}/${INDEX}" > /dev/null 2>&1 && \
      log "Deleted index: ${INDEX}" || log "Index ${INDEX} not found or already deleted"
  done
fi

# ── Trigger re-index via API ─────────────────────────────────────────────────
log "Triggering project index rebuild..."
RESPONSE=$(curl -sf -X POST "${API_BASE_URL}/v1/search/reindex/projects" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}' \
  -w "\n%{http_code}" 2>/dev/null || echo '{"error": "request failed"}\n000')
HTTP_CODE=$(echo "${RESPONSE}" | tail -1)
log "Project reindex: HTTP ${HTTP_CODE}"

log "Triggering document index rebuild..."
RESPONSE=$(curl -sf -X POST "${API_BASE_URL}/v1/search/reindex/documents" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}' \
  -w "\n%{http_code}" 2>/dev/null || echo '{"error": "request failed"}\n000')
HTTP_CODE=$(echo "${RESPONSE}" | tail -1)
log "Document reindex: HTTP ${HTTP_CODE}"

log "Triggering marketplace index rebuild..."
RESPONSE=$(curl -sf -X POST "${API_BASE_URL}/v1/search/reindex/marketplace" \
  -H "${AUTH_HEADER}" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}' \
  -w "\n%{http_code}" 2>/dev/null || echo '{"error": "request failed"}\n000')
HTTP_CODE=$(echo "${RESPONSE}" | tail -1)
log "Marketplace reindex: HTTP ${HTTP_CODE}"

log "Search index rebuild complete ✅"
log "Note: Indexing runs asynchronously. Monitor /v1/admin/system-health for progress."
