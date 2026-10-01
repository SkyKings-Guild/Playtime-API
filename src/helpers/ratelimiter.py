from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from enum import IntEnum
from inspect import isawaitable
from time import monotonic

from fastapi import Depends, HTTPException
from starlette.requests import Request
from starlette.responses import Response


Identifier = Callable[[Request], str | Awaitable[str]]


class Duration(IntEnum):
    MILLISECOND = 1
    SECOND = 1000
    MINUTE = SECOND * 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24


class Rate:
    def __init__(self, limit: int, period: int) -> None:
        if limit < 1:
            raise ValueError("limit must be greater than zero")
        if period < 1:
            raise ValueError("period must be greater than zero")
        self.limit = limit
        self.period = period


class Limiter:
    def __init__(self, rate: Rate) -> None:
        self.rate = rate
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)

    async def try_acquire_async(self, key: str) -> bool:
        now = monotonic()
        window_start = now - (self.rate.period / 1000)
        requests = self._requests[key]

        while requests and requests[0] <= window_start:
            requests.popleft()

        if len(requests) >= self.rate.limit:
            return False

        requests.append(now)
        return True


async def default_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client = forwarded_for.split(",", 1)[0].strip()
    elif request.client is not None:
        client = request.client.host
    else:
        client = "unknown"
    return f"{client}:{request.url.path}"


class _RateLimiter:
    """Use the in-process limiter as a FastAPI dependency."""

    def __init__(
        self,
        limiter: Limiter,
        identifier: Identifier = default_identifier,
    ) -> None:
        self.limiter = limiter
        self.identifier = identifier

    async def __call__(self, request: Request, response: Response) -> None:
        key = self.identifier(request)
        if isawaitable(key):
            key = await key

        allowed = await self.limiter.try_acquire_async(key)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
            )


def RateLimiter(
    limiter: Limiter,
    identifier: Identifier = default_identifier,
):
    return Depends(_RateLimiter(limiter, identifier))


__all__ = ["Duration", "Limiter", "Rate", "RateLimiter"]
