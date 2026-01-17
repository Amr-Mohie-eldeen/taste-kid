from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api.db import get_engine


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


def register_user(*, email: str, password_hash: str, display_name: str | None) -> int:
    engine = get_engine()
    normalized_email = email.strip().lower()

    q_insert_user = text("INSERT INTO users (display_name) VALUES (:display_name) RETURNING id")
    q_insert_credentials = text(
        """
        INSERT INTO user_credentials (user_id, email, password_hash)
        VALUES (:user_id, :email, :password_hash)
        """
    )

    try:
        with engine.begin() as conn:
            user_row = conn.execute(q_insert_user, {"display_name": display_name}).first()
            if user_row is None:
                raise RuntimeError("Failed to create user")
            user_id = int(user_row[0])

            conn.execute(
                q_insert_credentials,
                {
                    "user_id": user_id,
                    "email": normalized_email,
                    "password_hash": password_hash,
                },
            )
    except IntegrityError as exc:
        raise EmailAlreadyRegisteredError("Email already registered") from exc

    return user_id


def authenticate_user(*, email: str, password: str) -> int:
    engine = get_engine()
    normalized_email = email.strip().lower()

    q = text(
        """
        SELECT user_id, password_hash
        FROM user_credentials
        WHERE email = :email
        """
    )

    with engine.begin() as conn:
        row = conn.execute(q, {"email": normalized_email}).mappings().first()

    if not row:
        raise InvalidCredentialsError("Invalid credentials")

    from api.auth.passwords import verify_password

    if not verify_password(password, row["password_hash"]):
        raise InvalidCredentialsError("Invalid credentials")

    return int(row["user_id"])
