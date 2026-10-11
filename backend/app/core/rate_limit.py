import asyncio
import hashlib
import json
from time import monotonic

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.config import Environment, Settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Production budgets are atomic across workers; storage failure denies requests."""

    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings
        self.memory: dict[str, tuple[int, float]] = {}

    async def allowed(self, request: Request, key: str, limit: int, seconds: int) -> bool:
        digest = hashlib.sha256(key.encode()).hexdigest()
        if self.settings.app_env is Environment.PRODUCTION:
            redis = request.app.state.redis
            script = (
                "local n=redis.call('INCR',KEYS[1]); "
                "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]); end; return n"
            )
            result = await redis.eval(script, 1, "medguide:budget:" + digest, seconds)
            return int(result) <= limit
        now = monotonic()
        self.memory = {k: v for k, v in self.memory.items() if v[1] > now}
        if digest not in self.memory and len(self.memory) >= 10000:
            return False
        count, until = self.memory.get(digest, (0, now + seconds))
        self.memory[digest] = (count + 1, until)
        return count < limit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not request.url.path.startswith(self.settings.api_v1_prefix):
            return await call_next(request)
        request.state.take_budget = self.allowed
        address = request.client.host if request.client else "unknown"
        try:
            if not await self.allowed(request, "ip:" + address, 300, 60):
                return JSONResponse({"detail": "Request limit reached"}, status_code=429)
            auth_path = request.url.path.removeprefix(self.settings.api_v1_prefix)
            auth_request = request.method == "POST" and auth_path in {
                "/auth/login",
                "/auth/register",
            }
            body = bytearray()
            if request.method in {"POST", "PATCH", "PUT"}:
                maximum = 8192 if auth_request else 65536
                if int(request.headers.get("content-length", "0")) > maximum:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
                async with asyncio.timeout(10):
                    async for chunk in request.stream():
                        body.extend(chunk)
                        if len(body) > maximum:
                            return JSONResponse({"detail": "Request too large"}, status_code=413)
                request._body = bytes(body)
            if auth_request:
                if not await self.allowed(request, "auth-ip:" + address, 30, 900):
                    return JSONResponse({"detail": "Authentication limit reached"}, status_code=429)
                try:
                    payload = json.loads(body)
                    email = payload.get("email") if isinstance(payload, dict) else None
                except (ValueError, UnicodeDecodeError):
                    email = None
                if isinstance(email, str) and not await self.allowed(
                    request, "auth-account:" + email.strip().lower(), 20, 900
                ):
                    return JSONResponse({"detail": "Authentication limit reached"}, status_code=429)
        except Exception:
            return JSONResponse({"detail": "Service temporarily unavailable"}, status_code=503)
        return await call_next(request)
