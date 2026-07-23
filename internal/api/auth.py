"""
𒀭 Auth & Middleware
"""

import os
import time
import jwt
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

# ─── Auth ───

SECRET_KEY = os.getenv("JWT_SECRET", "nabu-dev-secret-change-in-production")
ALGORITHM = "RS256"  # Use RS256 for production
ISSUER = "nabu"

security = HTTPBearer(auto_error=False)


async def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return machine payload."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,  # In production: use public key for RS256
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience="nabu-mining",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def get_current_machine(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current authenticated machine."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization")
    return await verify_token(credentials.credentials)


def create_machine_token(machine_id: str, tier: str, ttl_hours: int = 720) -> str:
    """Create JWT for a mining machine."""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": machine_id,
        "tier": tier,
        "iat": now,
        "exp": now + datetime.timedelta(hours=ttl_hours),
        "iss": ISSUER,
        "aud": "nabu-mining",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ─── Rate Limiting Middleware ───

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-machine rate limiting with tiered quotas."""
    
    TIER_LIMITS = {
        "mining": {"requests_per_minute": 120, "burst": 30},
        "mining_high": {"requests_per_minute": 600, "burst": 100},
        "admin": {"requests_per_minute": 60, "burst": 20},
    }

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis = redis_client

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for health checks
        if request.url.path in ["/health", "/ready", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get machine from auth
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)  # Let auth middleware handle
        
        token = auth[7:]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            machine_id = payload.get("sub")
            tier = payload.get("tier", "mining")
        except:
            return await call_next(request)  # Let auth middleware handle

        # Check rate limit
        if self.redis and machine_id:
            limit = self.TIER_LIMITS.get(tier, self.TIER_LIMITS["mining"])
            key = f"ratelimit:{machine_id}"
            
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, 60)
            
            if current > limit["requests_per_minute"]:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded", "limit": limit["requests_per_minute"]},
                    headers={
                        "X-RateLimit-Limit": str(limit["requests_per_minute"]),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": "60",
                    }
                )

        return await call_next(request)


# ─── Logging Middleware ───

class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        
        # Log request
        print(f"📥 {request.method} {request.url.path} from {request.client.host}")
        
        response = await call_next(request)
        
        duration = time.time() - start
        print(f"📤 {request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)")
        
        response.headers["X-Process-Time"] = str(duration)
        return response