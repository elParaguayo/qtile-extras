from _typeshed import Incomplete
from stravalib import exc as exc
from typing import NamedTuple

def total_seconds(td): ...

class RequestRate(NamedTuple):
    short_usage: Incomplete
    long_usage: Incomplete
    short_limit: Incomplete
    long_limit: Incomplete

def get_rates_from_response_headers(headers): ...
def get_seconds_until_next_quarter(now: Incomplete | None = ...): ...
def get_seconds_until_next_day(now: Incomplete | None = ...): ...

class XRateLimitRule:
    log: Incomplete
    rate_limits: Incomplete
    limit_time_invalid: int
    force_limits: Incomplete
    def __init__(self, limits, force_limits: bool = ...) -> None: ...
    @property
    def limit_timeout(self): ...
    def __call__(self, response_headers) -> None: ...

class SleepingRateLimitRule:
    log: Incomplete
    priority: Incomplete
    short_limit: Incomplete
    long_limit: Incomplete
    force_limits: Incomplete
    def __init__(self, priority: str = ..., short_limit: int = ..., long_limit: int = ..., force_limits: bool = ...) -> None: ...
    def __call__(self, response_headers) -> None: ...

class RateLimitRule:
    log: Incomplete
    timeframe: Incomplete
    requests: Incomplete
    tab: Incomplete
    raise_exc: Incomplete
    def __init__(self, requests, seconds, raise_exc: bool = ...) -> None: ...
    def __call__(self, args) -> None: ...

class RateLimiter:
    log: Incomplete
    rules: Incomplete
    def __init__(self) -> None: ...
    def __call__(self, args) -> None: ...

class DefaultRateLimiter(RateLimiter):
    def __init__(self) -> None: ...
