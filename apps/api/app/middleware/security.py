"""Security middleware: HTTP headers, rate limiting, body size enforcement.

All three are implemented as pure ASGI middleware (no BaseHTTPMiddleware)
so they are compatible with streaming responses (SSE, chunked).
"""

import base64
import json
import time

import structlog
import redis.asyncio as aioredis
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

logger = structlog.get_logger()

# ── 1. Security Headers ───────────────────────────────────────────────────────


class SecurityHeadersMiddleware:
    """Append security headers to every HTTP response."""

    _STATIC_HEADERS = [
        ("x-content-type-options", "nosniff"),
        ("x-frame-options", "DENY"),
        # XSS-Protection 0 is the modern recommendation (disables the broken IE filter)
        ("x-xss-protection", "0"),
        ("referrer-policy", "strict-origin-when-cross-origin"),
        ("permissions-policy", "geolocation=(), microphone=(), camera=(), payment=()"),
    ]
    _HSTS_HEADER = ("strict-transport-security", "max-age=63072000; includeSubDomains; preload")

    def __init__(self, app: ASGIApp, is_production: bool = False) -> None:
        self.app = app
        self._headers = list(self._STATIC_HEADERS)
        if is_production:
            self._headers.append(self._HSTS_HEADER)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def _send(message: dict) -> None:
            if message["type"] == "http.response.start":
                raw = MutableHeaders(scope=message)
                for name, value in self._headers:
                    raw.append(name, value)
                # Strip server fingerprint
                raw.update({"server": "SCR"})
            await send(message)

        await self.app(scope, receive, _send)


# ── 2. Request Body Size Limiter ──────────────────────────────────────────────


class RequestBodySizeLimitMiddleware:
    """Reject requests whose Content-Length exceeds max_size before they hit handlers."""

    def __init__(self, app: ASGIApp, max_bytes: int = 52_428_800) -> None:  # 50 MB
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_cl = headers.get(b"content-length")
        if raw_cl:
            try:
                if int(raw_cl) > self.max_bytes:
                    body = json.dumps({"detail": "Request body too large. Maximum 50 MB."}).encode()
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 413,
                            "headers": [
                                (b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode()),
                            ],
                        }
                    )
                    await send({"type": "http.response.body", "body": body, "more_body": False})
                    return
            except ValueError:
                pass  # Malformed header — let downstream handle it

        await self.app(scope, receive, send)


# ── 3. Redis Sliding-Window Rate Limiter ──────────────────────────────────────


# (path_prefix, requests_allowed, window_seconds)
# More specific prefixes must come before generic ones.
_RATE_RULES: list[tuple[str, int, int]] = [
    ("/auth/", 20, 60),          # Auth: 20/min per IP (brute-force protection)
    ("/webhooks/", 200, 60),     # Webhooks: 200/min (Clerk sends many events)
    ("/ralph/", 60, 60),         # Ralph AI: 60/min per IP
    ("/investor-signal-score/calculate", 10, 60),   # Score recalc: 10/min
    # Share links use the default 300/min IP limit (sufficient + doesn't break tests)
]
_DEFAULT_RATE: tuple[int, int] = (300, 60)  # 300 req/min default per IP

# Org-level rate limits — applied to authenticated requests in addition to IP limits.
# Higher thresholds than IP limits (legitimate orgs make many requests), but prevent
# single-org abuse from affecting other tenants.
# (path_prefix, requests_allowed, window_seconds)
_ORG_RATE_RULES: list[tuple[str, int, int]] = [
    ("/ralph/", 200, 60),                        # 200 AI calls/min per org
    ("/signal-score/calculate", 50, 60),         # 50 score calcs/min per org
    ("/dataroom/bulk/analyze", 20, 60),          # 20 bulk analyses/min per org
    ("/dataroom/upload", 100, 60),               # 100 uploads/min per org
    ("/webhooks/", 500, 60),                     # 500 webhook events/min per org
    ("/", 1000, 60),                             # 1000 req/min default per org
]

_SKIP_PATHS: frozenset[str] = frozenset(
    ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
)


class RateLimitMiddleware:
    """IP-based + org-based sliding-window rate limiter backed by Redis.

    Two layers of protection:
    1. IP-level limits — brute-force / unauthenticated request protection.
    2. Org-level limits — prevents a single tenant from monopolising capacity.
       The org_id is extracted by peeking at the JWT payload (no verification —
       rate limiting is best-effort; actual auth happens in the route handler).

    Fails *open* if Redis is unavailable — requests are never blocked due to
    a Redis outage.  Rate-limit headers are added to all passing responses.
    """

    def __init__(self, app: ASGIApp, redis_url: str, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    def _client(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
        return self._redis

    @staticmethod
    def _extract_org_id(headers: dict[bytes, bytes]) -> str | None:
        """Peek at the JWT payload to extract org_id for rate limiting.

        Does NOT verify the signature — auth is handled by the route dependency.
        Returns None if the header is absent or the token is malformed.
        """
        try:
            auth = headers.get(b"authorization", b"").decode()
            if not auth.startswith("Bearer "):
                return None
            payload_b64 = auth[7:].split(".")[1]
            # Standard base64url padding
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload_b64))
            # Try the SCR custom claim first, then standard metadata
            return (
                claims.get("org_id")
                or claims.get("metadata", {}).get("org_id")
            )
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    async def _sliding_window(
        redis: aioredis.Redis,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int]:
        """Execute sliding-window counter. Returns (allowed, remaining)."""
        now = time.time()
        pipe = redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        pipe.expire(key, window + 1)
        results = await pipe.execute()
        count: int = results[2]
        return count <= limit, max(0, limit - count)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        raw_headers: dict[bytes, bytes] = {k: v for k, v in scope.get("headers", [])}

        # Resolve client IP (respect X-Forwarded-For from a trusted proxy)
        xff = raw_headers.get(b"x-forwarded-for", b"").decode()
        ip = xff.split(",")[0].strip() if xff else (scope.get("client") or ["unknown"])[0]

        # Strip /v1 prefix for consistent rule matching
        effective_path = path[3:] if path.startswith("/v1") else path

        # ── IP-level check ─────────────────────────────────────────────────────
        ip_limit, ip_window = _DEFAULT_RATE
        for prefix, r_lim, r_win in _RATE_RULES:
            if effective_path.startswith(prefix):
                ip_limit, ip_window = r_lim, r_win
                break

        ip_allowed = True
        ip_remaining = ip_limit
        try:
            redis = self._client()
            segment = (
                effective_path.split("/")[1]
                if "/" in effective_path[1:]
                else effective_path.lstrip("/")
            )
            ip_allowed, ip_remaining = await self._sliding_window(
                redis, f"rl:ip:{ip}:{segment}", ip_limit, ip_window
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("rate_limit.ip_redis_error", error=str(exc))

        if not ip_allowed:
            return await self._send_429(
                send,
                ip_limit,
                ip_window,
                reason="ip_limit_exceeded",
            )

        # ── Org-level check (authenticated requests only) ──────────────────────
        org_id = self._extract_org_id(raw_headers)
        org_limit, org_window = 1000, 60  # defaults
        org_remaining = org_limit
        if org_id:
            for prefix, r_lim, r_win in _ORG_RATE_RULES:
                if effective_path.startswith(prefix):
                    org_limit, org_window = r_lim, r_win
                    break
            try:
                redis = self._client()
                org_allowed, org_remaining = await self._sliding_window(
                    redis, f"rl:org:{org_id}:{segment}", org_limit, org_window
                )
                if not org_allowed:
                    return await self._send_429(
                        send,
                        org_limit,
                        org_window,
                        reason="org_limit_exceeded",
                        extra_headers=[
                            (b"x-ratelimit-org-limit", str(org_limit).encode()),
                            (b"x-ratelimit-org-remaining", b"0"),
                        ],
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("rate_limit.org_redis_error", error=str(exc))

        # ── Pass-through — annotate response headers ────────────────────────────
        async def _send_with_rl_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                h = MutableHeaders(scope=message)
                h.append("x-ratelimit-limit", str(ip_limit))
                h.append("x-ratelimit-remaining", str(ip_remaining))
                h.append("x-ratelimit-window", str(ip_window))
                if org_id:
                    h.append("x-ratelimit-org-limit", str(org_limit))
                    h.append("x-ratelimit-org-remaining", str(org_remaining))
            await send(message)

        await self.app(scope, receive, _send_with_rl_headers)

    @staticmethod
    async def _send_429(
        send: Send,
        limit: int,
        window: int,
        reason: str = "rate_limit_exceeded",
        extra_headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        body = json.dumps({"detail": "Too many requests. Please slow down.", "reason": reason}).encode()
        headers: list[tuple[bytes, bytes]] = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"retry-after", str(window).encode()),
            (b"x-ratelimit-limit", str(limit).encode()),
            (b"x-ratelimit-remaining", b"0"),
            (b"x-ratelimit-window", str(window).encode()),
            *(extra_headers or []),
        ]
        await send({"type": "http.response.start", "status": 429, "headers": headers})
        await send({"type": "http.response.body", "body": body, "more_body": False})
