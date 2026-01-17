from passlib.context import CryptContext

_password_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return _password_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_ctx.verify(password, password_hash)
