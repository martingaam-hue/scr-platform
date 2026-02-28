"""Security middleware: HTTP headers, rate limiting, body size enforcement.

All three are implemented as pure ASGI middleware (no BaseHTTPMiddleware)
so they are compatible with streaming responses (SSE, chunked).
"""

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
    ("/auth/", 20, 60),          # Auth: 20/min per IP
    ("/webhooks/", 200, 60),     # Webhooks: 200/min (Clerk sends many events)
    ("/ralph/", 60, 60),         # Ralph AI: 60/min
    ("/investor-signal-score/calculate", 10, 60),  # Score recalc: 10/min
]
_DEFAULT_RATE: tuple[int, int] = (300, 60)  # 300 req/min default

_SKIP_PATHS: frozenset[str] = frozenset(
    ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
)


class RateLimitMiddleware:
    """IP-based sliding-window rate limiter backed by Redis.

    Fails *open* if Redis is unavailable — requests are never blocked due to
    a Redis outage.  Rate-limit headers are always added to passing responses.
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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        # Resolve client IP (respect X-Forwarded-For from trusted proxy)
        headers = {k: v for k, v in scope.get("headers", [])}
        xff = headers.get(b"x-forwarded-for", b"").decode()
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            client = scope.get("client")
            ip = client[0] if client else "unknown"

        # Match rate rule
        limit, window = _DEFAULT_RATE
        for prefix, r_lim, r_win in _RATE_RULES:
            if path.startswith(prefix):
                limit, window = r_lim, r_win
                break

        # Sliding window via Redis sorted set
        allowed = True
        remaining = limit
        try:
            redis = self._client()
            # Group by top-level path segment to avoid key explosion
            segment = path.split("/")[1] if "/" in path[1:] else path.lstrip("/")
            key = f"rl:{ip}:{segment}"
            now = time.time()
            window_start = now - window

            pipe = redis.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, window + 1)
            results = await pipe.execute()

            count: int = results[2]
            remaining = max(0, limit - count)
            allowed = count <= limit

        except Exception as exc:
            logger.warning("rate_limit.redis_error", error=str(exc))
            # Fail open — don't block requests when Redis is down

        if not allowed:
            body = json.dumps({"detail": "Too many requests. Please slow down."}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"retry-after", str(window).encode()),
                        (b"x-ratelimit-limit", str(limit).encode()),
                        (b"x-ratelimit-remaining", b"0"),
                        (b"x-ratelimit-window", str(window).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body, "more_body": False})
            return

        # Pass-through — annotate response with rate limit headers
        async def _send_with_rl_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers_obj = MutableHeaders(scope=message)
                headers_obj.append("x-ratelimit-limit", str(limit))
                headers_obj.append("x-ratelimit-remaining", str(remaining))
                headers_obj.append("x-ratelimit-window", str(window))
            await send(message)

        await self.app(scope, receive, _send_with_rl_headers)
