from __future__ import annotations

import json
import time
import urllib.request
import uuid

import jwt

from api.config import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    KEYCLOAK_AUDIENCE,
    KEYCLOAK_ISSUER_URL,
    KEYCLOAK_JWKS_URL,
)


class InvalidTokenError(ValueError):
    pass


def create_access_token(*, user_id: int) -> str:
    now = int(time.time())
    exp = now + JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": exp,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


_JWKS_CACHE: tuple[float, dict] | None = None
_JWKS_CACHE_TTL_S = 60.0


def _load_jwks(jwks_url: str) -> dict:
    global _JWKS_CACHE

    now = time.time()
    if _JWKS_CACHE is not None:
        cached_at, cached = _JWKS_CACHE
        if now - cached_at < _JWKS_CACHE_TTL_S:
            return cached

    with urllib.request.urlopen(jwks_url, timeout=2.0) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))

    if not isinstance(payload, dict) or "keys" not in payload:
        raise InvalidTokenError("Invalid JWKS payload")

    _JWKS_CACHE = (now, payload)
    return payload


def _decode_keycloak_token(token: str) -> dict:
    if not KEYCLOAK_JWKS_URL or not KEYCLOAK_ISSUER_URL or not KEYCLOAK_AUDIENCE:
        raise InvalidTokenError("Keycloak verification not configured")

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise InvalidTokenError("Invalid token header")

    jwks = _load_jwks(KEYCLOAK_JWKS_URL)
    key = None
    for candidate in jwks.get("keys", []):
        if isinstance(candidate, dict) and candidate.get("kid") == kid:
            key = candidate
            break

    if key is None:
        raise InvalidTokenError("Unknown token key")

    try:
        public_key = jwt.PyJWK.from_dict(key).key
    except Exception as exc:
        raise InvalidTokenError("Invalid JWKS key") from exc

    try:
        return jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER_URL,
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid token") from exc


def decode_token(token: str) -> dict:
    if KEYCLOAK_JWKS_URL and KEYCLOAK_ISSUER_URL and KEYCLOAK_AUDIENCE:
        return _decode_keycloak_token(token)

    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid token") from exc
