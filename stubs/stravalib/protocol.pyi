import abc

from _typeshed import Incomplete
from stravalib import exc as exc

class ApiV3(metaclass=abc.ABCMeta):
    server: str
    api_base: str
    log: Incomplete
    access_token: Incomplete
    rsession: Incomplete
    rate_limiter: Incomplete
    def __init__(
        self,
        access_token: Incomplete | None = ...,
        requests_session: Incomplete | None = ...,
        rate_limiter: Incomplete | None = ...,
    ) -> None: ...
    def authorization_url(
        self,
        client_id,
        redirect_uri,
        approval_prompt: str = ...,
        scope: Incomplete | None = ...,
        state: Incomplete | None = ...,
    ): ...
    def exchange_code_for_token(self, client_id, client_secret, code): ...
    def refresh_access_token(self, client_id, client_secret, refresh_token): ...
    def resolve_url(self, url): ...
    def get(self, url, check_for_errors: bool = ..., **kwargs): ...
    def post(
        self, url, files: Incomplete | None = ..., check_for_errors: bool = ..., **kwargs
    ): ...
    def put(self, url, check_for_errors: bool = ..., **kwargs): ...
    def delete(self, url, check_for_errors: bool = ..., **kwargs): ...
