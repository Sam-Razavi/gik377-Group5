from datetime import UTC, datetime, timedelta

import bcrypt
import pyotp
from jose import JWTError, jwt

from core.config import settings


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError:
        return None


def generate_2fa_secret() -> str:
    return pyotp.random_base32()


def get_2fa_provisioning_uri(email: str, secret: str) -> str:
    totp = pyotp.TOTP(secret)

    return totp.provisioning_uri(
        name=email,
        issuer_name="Nordic Digital Solutions",
    )


def verify_2fa_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)

    return totp.verify(
        code,
        valid_window=1,
    )


def create_2fa_temp_token(email: str) -> str:
    to_encode = {
        "sub": email,
        "purpose": "2fa",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    return encoded_jwt


def decode_2fa_temp_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        if payload.get("purpose") != "2fa":
            return None

        email = payload.get("sub")

        if not email:
            return None

        return email

    except JWTError:
        return None