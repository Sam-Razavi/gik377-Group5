from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.auth.models import User
from services.auth.repository import create_user, get_user_by_email
from services.auth.schemas import UserCreate
from services.auth.security import decode_access_token, verify_password


def register_user(db: Session, user_data: UserCreate) -> User:
    existing_user = get_user_by_email(db, user_data.email)

    if existing_user:
        raise ValueError("A user with this email already exists.")

    return create_user(db, user_data)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def get_current_user_from_token(db: Session, token: str) -> User:
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    email = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing user information",
        )

    user = get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user