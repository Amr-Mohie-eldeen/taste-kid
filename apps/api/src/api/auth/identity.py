from __future__ import annotations

from sqlalchemy import text

from api.db import get_engine
from api.users import create_user


class IdentityProviderNotSupportedError(ValueError):
    pass


def get_or_create_user_id_for_subject(*, provider: str, subject: str, display_name: str | None = None) -> int:
    if not provider:
        raise IdentityProviderNotSupportedError("Missing identity provider")

    engine = get_engine()

    q_select = text(
        """
        SELECT user_id
        FROM user_identities
        WHERE provider = :provider AND subject = :subject
        """
    )

    with engine.begin() as conn:
        row = conn.execute(q_select, {"provider": provider, "subject": subject}).mappings().first()
        if row:
            return int(row["user_id"])

        user_id = create_user(display_name=display_name)

        q_insert = text(
            """
            INSERT INTO user_identities (provider, subject, user_id)
            VALUES (:provider, :subject, :user_id)
            """
        )
        conn.execute(q_insert, {"provider": provider, "subject": subject, "user_id": user_id})

    return int(user_id)
