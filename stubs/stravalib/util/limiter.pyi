from stravalib import exc as exc
from typing import Any, NamedTuple

def total_seconds(td): ...

class RequestRate(NamedTuple):
    short_usage: Any
    long_usage: Any
    short_limit: Any
    long_limit: Any

def get_rates_from_response_headers(headers): ...
def get_seconds_until_next_quarter(now: Any | None = ...): ...
def get_seconds_until_next_day(now: Any | None = ...): ...

class XRateLimitRule:
    log: Any
    rate_limits: Any
    limit_time_invalid: int
    force_limits: Any
    def __init__(self, limits, force_limits: bool = ...) -> None: ...
    @property
    def limit_timeout(self): ...
    def __call__(self, response_headers) -> None: ...

class SleepingRateLimitRule:
    log: Any
    priority: Any
    short_limit: Any
    long_limit: Any
    force_limits: Any
    def __init__(self, priority: str = ..., short_limit: int = ..., long_limit: int = ..., force_limits: bool = ...) -> None: ...
    def __call__(self, response_headers) -> None: ...

class RateLimitRule:
    log: Any
    timeframe: Any
    requests: Any
    tab: Any
    raise_exc: Any
    def __init__(self, requests, seconds, raise_exc: bool = ...) -> None: ...
    def __call__(self, args) -> None: ...

class RateLimiter:
    log: Any
    rules: Any
    def __init__(self) -> None: ...
    def __call__(self, args) -> None: ...

class DefaultRateLimiter(RateLimiter):
    def __init__(self) -> None: ...
