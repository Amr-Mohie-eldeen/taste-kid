from __future__ import annotations

import json
import urllib.parse
import urllib.request


class KeycloakError(RuntimeError):
    pass


def _request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, data=None):
    req = urllib.request.Request(url, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)

    payload = None
    if data is not None:
        if isinstance(data, dict):
            payload = json.dumps(data).encode("utf-8")
            req.add_header("Content-Type", "application/json")
        elif isinstance(data, bytes):
            payload = data
        else:
            raise TypeError("Unsupported request body")

    try:
        with urllib.request.urlopen(req, data=payload, timeout=10.0) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except Exception as exc:
        raise KeycloakError(f"Keycloak request failed: {method} {url}") from exc


def _request_no_body(url: str, *, method: str, headers: dict[str, str] | None = None) -> None:
    req = urllib.request.Request(url, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)

    with urllib.request.urlopen(req, timeout=10.0):  # noqa: S310
        return


def get_admin_access_token(*, base_url: str, realm: str, username: str, password: str) -> str:
    token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
    body = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": username,
            "password": password,
        }
    ).encode("utf-8")

    req = urllib.request.Request(token_url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise KeycloakError("Failed to authenticate to Keycloak admin") from exc

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise KeycloakError("Keycloak admin token missing access_token")

    return access_token


def create_user(
    *,
    base_url: str,
    realm: str,
    admin_token: str,
    email: str,
    password: str,
    display_name: str | None,
) -> str:
    url = f"{base_url}/admin/realms/{realm}/users"

    payload: dict[str, object] = {
        "enabled": True,
        "email": email,
        "username": email,
        "emailVerified": True,
    }

    if display_name:
        payload["firstName"] = display_name

    _request_json(
        url,
        method="POST",
        headers={"Authorization": f"Bearer {admin_token}"},
        data=payload,
    )

    # Fetch user id by email
    q = urllib.parse.urlencode({"email": email})
    search_url = f"{base_url}/admin/realms/{realm}/users?{q}"

    users = _request_json(
        search_url,
        method="GET",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    if not isinstance(users, list) or not users:
        raise KeycloakError("Keycloak user not found after creation")

    user_id = users[0].get("id")
    if not isinstance(user_id, str) or not user_id:
        raise KeycloakError("Keycloak user lookup missing id")

    # Set password
    pw_url = f"{base_url}/admin/realms/{realm}/users/{user_id}/reset-password"
    pw_payload = {"type": "password", "value": password, "temporary": False}

    _request_json(
        pw_url,
        method="PUT",
        headers={"Authorization": f"Bearer {admin_token}"},
        data=pw_payload,
    )

    return user_id


def password_grant(
    *,
    base_url: str,
    realm: str,
    client_id: str,
    username: str,
    password: str,
    scope: str,
) -> dict:
    token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"

    body = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": client_id,
            "username": username,
            "password": password,
            "scope": scope,
        }
    ).encode("utf-8")

    req = urllib.request.Request(token_url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise KeycloakError("Invalid credentials") from exc

    return payload


def refresh_grant(
    *,
    base_url: str,
    realm: str,
    client_id: str,
    refresh_token: str,
) -> dict:
    token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"

    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")

    req = urllib.request.Request(token_url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise KeycloakError("Failed to refresh token") from exc

    return payload
