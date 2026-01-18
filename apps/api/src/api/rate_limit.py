from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from api.auth.jwt import InvalidTokenError, decode_token
from api.config import DEFAULT_RATE_LIMIT_LOGIN, DEFAULT_RATE_LIMIT_REGISTER, RATE_LIMIT_DEFAULT


def _rate_limit_key(request: Request) -> str:
    authorization = request.headers.get("authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                payload = decode_token(token)
            except InvalidTokenError:
                payload = None
            if payload:
                subject = payload.get("sub")
                if isinstance(subject, str) and subject:
                    return f"user:{subject}"

    return get_remote_address(request)


def register_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_REGISTER", DEFAULT_RATE_LIMIT_REGISTER)


def login_rate_limit() -> str:
    return os.getenv("RATE_LIMIT_LOGIN", DEFAULT_RATE_LIMIT_LOGIN)


limiter = Limiter(key_func=_rate_limit_key, default_limits=[RATE_LIMIT_DEFAULT])
