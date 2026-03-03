#!/usr/bin/env bash
# SCR Platform — Vercel Deployment Script
# Run this in your own terminal: bash deploy-vercel.sh
set -euo pipefail

GREEN='\033[0;32m' CYAN='\033[0;36m' YELLOW='\033[1;33m' NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

# ── 1. Install Vercel CLI ────────────────────────────────────────────────────
if ! command -v vercel &>/dev/null; then
  info "Installing Vercel CLI..."
  sudo npm install -g vercel
fi
success "Vercel CLI: $(vercel --version)"

# ── 2. Login & link ──────────────────────────────────────────────────────────
info "Logging in to Vercel (browser will open)..."
vercel login

info "Linking project to Vercel..."
vercel link --yes

# ── 3. Set environment variables ─────────────────────────────────────────────
info "Setting environment variables..."

set_env() {
  local KEY="$1" VAL="$2" TARGET="${3:-production}"
  printf '%s' "$VAL" | vercel env add "$KEY" "$TARGET" --force 2>/dev/null \
    && echo "  ✓ $KEY" \
    || echo "  ! $KEY (may already exist — check dashboard)"
}

# Known from ECS task definition
set_env NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY "pk_test_bmF0aW9uYWwtcGFuZ29saW4tMi5jbGVyay5hY2NvdW50cy5kZXYk"
set_env CLERK_SECRET_KEY                  "sk_test_v0GU5PqSfwQAqLY0x1Uq2QhMORS3zObQu3OldPCZj9"
set_env NEXT_PUBLIC_SENTRY_DSN            "https://ac964ac1b2ab7a0fe043315464ed4eb8@o4510976260767744.ingest.de.sentry.io/4510976299827280"
set_env NEXT_PUBLIC_APP_ENV               "staging"
set_env NEXT_PUBLIC_API_URL               "https://api.pampgroup.com"

# Also add to preview environments
set_env NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY "pk_test_bmF0aW9uYWwtcGFuZ29saW4tMi5jbGVyay5hY2NvdW50cy5kZXYk" "preview"
set_env CLERK_SECRET_KEY                  "sk_test_v0GU5PqSfwQAqLY0x1Uq2QhMORS3zObQu3OldPCZj9" "preview"
set_env NEXT_PUBLIC_API_URL               "https://api.pampgroup.com" "preview"
set_env NEXT_PUBLIC_APP_ENV               "staging" "preview"

# Optional: prompt for Sentry tokens (needed for source maps in build)
echo ""
warn "Optional: Sentry source map upload (for readable stack traces)"
read -rp "  SENTRY_ORG (leave blank to skip): " SENTRY_ORG
if [[ -n "$SENTRY_ORG" ]]; then
  set_env SENTRY_ORG "$SENTRY_ORG"
  read -rp "  SENTRY_PROJECT: " SENTRY_PROJECT
  set_env SENTRY_PROJECT "$SENTRY_PROJECT"
  read -rsp "  SENTRY_AUTH_TOKEN: " SENTRY_AUTH_TOKEN; echo
  set_env SENTRY_AUTH_TOKEN "$SENTRY_AUTH_TOKEN"
fi

success "Environment variables configured"

# ── 4. Deploy ────────────────────────────────────────────────────────────────
info "Deploying to Vercel (production)..."
vercel --prod

# ── 5. Add custom domain ─────────────────────────────────────────────────────
info "Adding custom domain app.pampgroup.com..."
vercel domains add app.pampgroup.com || warn "Domain add failed — add manually in Vercel dashboard"

# ── 6. Print DNS instructions ────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Deployment complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Next step — DNS cutover in Route53:"
echo "  Change app.pampgroup.com → CNAME → cname.vercel-dns.com"
echo "  (Claude Code will handle this once you confirm deploy looks good)"
echo ""
