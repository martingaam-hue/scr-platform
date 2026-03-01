# Key Rotation Procedures

## Webhook Signing Secrets
Each webhook subscription has its own HMAC secret.

**Rotation steps:**
1. Call `POST /v1/webhooks/{id}/rotate-secret` (requires manage_settings permission)
2. The response contains `new_secret` — share with the webhook consumer
3. Consumer must update their signature verification immediately
4. Old secret is invalidated at rotation time

## AI Gateway API Key
Zero-downtime rotation using dual-key support.

**Rotation steps:**
1. Generate new key: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Set `AI_GATEWAY_API_KEY_PREVIOUS` = current key value
3. Set `AI_GATEWAY_API_KEY` = new key
4. Deploy AI gateway (now accepts both keys)
5. Update backend `AI_GATEWAY_API_KEY` env var to new key
6. Deploy backend
7. After 24 hours: clear `AI_GATEWAY_API_KEY_PREVIOUS`

## Fernet Encryption Key (CRM OAuth Tokens)
⚠️ WARNING: Rotating this key invalidates ALL encrypted CRM OAuth tokens.
All users with connected CRM integrations will need to re-authenticate.

**Rotation steps:**
1. Notify users that CRM connections will require re-authentication
2. Generate new key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
3. Set `SECRET_KEY` = new key
4. Deploy API
5. All CRM connections now show as disconnected — users must reconnect

## PostgreSQL Credentials
Standard credential rotation — update `DATABASE_URL` and `DATABASE_URL_SYNC` env vars, then restart API and Celery worker.

## Clerk Keys
Managed via Clerk dashboard. Update `CLERK_SECRET_KEY` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, then redeploy.
