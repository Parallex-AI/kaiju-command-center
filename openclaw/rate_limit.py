"""
V5.17 Phase 4 — Local in-memory rate limiting for OpenClaw admin endpoints.

Process-local only. No Redis, no external service, no fixed-cost infrastructure.
Resets on process restart. Not shared across Cloud Run instances.

Rate limit is disabled by default (OPENCLAW_ADMIN_RATE_LIMIT_RPM=0).
"""

import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)


# ---------------------------------------------------------------------------
# Category constants
# ---------------------------------------------------------------------------

class RateLimitCategory:
    STANDARD = "standard"   # status, write, validate
    SENSITIVE = "sensitive"  # rotate, delete


# ---------------------------------------------------------------------------
# Sliding-window rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Per-(token, category) sliding-window rate limiter.

    Thread-safe. In-memory only. State is lost on process restart.
    """

    _WINDOW_SECONDS = 60

    def __init__(self) -> None:
        self._buckets: Dict[tuple, deque] = {}
        self._lock = threading.Lock()

    def check(self, token: str, category: str, limit_rpm: int) -> dict:
        """
        Check and record a request attempt.

        Returns a dict with keys: allowed, limit, remaining, retry_after_seconds.
        Never stores or returns the token value.
        """
        if limit_rpm <= 0:
            return {"allowed": True, "limit": 0, "remaining": None, "retry_after_seconds": 0}

        now = time.monotonic()
        key = (token, category)
        cutoff = now - self._WINDOW_SECONDS

        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = deque()
            bucket = self._buckets[key]

            # Drop timestamps outside the sliding window
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) < limit_rpm:
                bucket.append(now)
                return {
                    "allowed": True,
                    "limit": limit_rpm,
                    "remaining": limit_rpm - len(bucket),
                    "retry_after_seconds": 0,
                }
            else:
                oldest = bucket[0]
                retry_after = max(1, int(oldest + self._WINDOW_SECONDS - now) + 1)
                return {
                    "allowed": False,
                    "limit": limit_rpm,
                    "remaining": 0,
                    "retry_after_seconds": retry_after,
                }

    def reset_for_tests(self) -> None:
        """Test-only: clear all rate limit state so scenarios start fresh."""
        with self._lock:
            self._buckets.clear()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_rate_limiter: Optional[RateLimiter] = None
_rl_init_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        with _rl_init_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()
    return _rate_limiter


# ---------------------------------------------------------------------------
# Route-level helper
# ---------------------------------------------------------------------------

def check_rate_limit(
    token: Optional[str],
    category: str,
    config=None,
) -> Tuple[bool, List[dict]]:
    """
    Check whether a token is within its rate limit for the given category.

    Returns (True, []) when allowed.
    Returns (False, [error_dict]) when denied — error dict includes retry_after_seconds.

    Must be called AFTER validate_api_auth and validate_tenant_access succeed.
    Only authenticated, scoped, tenant-allowed requests consume rate budget.
    """
    if config is None:
        from config import get_config
        config = get_config()

    if category == RateLimitCategory.SENSITIVE:
        limit_rpm = config.admin_rate_limit_sensitive_rpm
    else:
        limit_rpm = config.admin_rate_limit_rpm

    if limit_rpm <= 0:
        return True, []

    # When auth is disabled, token is None; use a shared anonymous bucket.
    effective_token = token if token is not None else "__anon__"

    result = get_rate_limiter().check(effective_token, category, limit_rpm)
    if result["allowed"]:
        return True, []

    from schemas import make_error
    err = make_error(
        "rate_limit_exceeded",
        f"Rate limit exceeded. Retry after {result['retry_after_seconds']} seconds.",
        recoverable=True,
        source="openclaw",
    )
    err["retry_after_seconds"] = result["retry_after_seconds"]
    return False, [err]
