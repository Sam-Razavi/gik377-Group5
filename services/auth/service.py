from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.auth.models import User
from services.auth.repository import (
    create_bankid_user,
    create_user,
    get_user_by_bankid_personal_number,
    get_user_by_email,
)
from services.auth.schemas import UserCreate
from services.auth.security import (
    create_access_token,
    decode_access_token,
    verify_password,
)


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


def get_or_create_bankid_user(
    db: Session,
    personal_number: str,
    full_name: str | None = None,
) -> User:
    user = get_user_by_bankid_personal_number(db, personal_number)

    if user:
        return user

    return create_bankid_user(
        db=db,
        personal_number=personal_number,
        full_name=full_name,
    )


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

def handle_completed_bankid_login(
    db: Session,
    personal_number: str,
    full_name: str | None = None,
) -> dict:
    user = get_or_create_bankid_user(
        db=db,
        personal_number=personal_number,
        full_name=full_name,
    )

    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }

def login_user(db: Session, email: str, password: str) -> dict:
    user = authenticate_user(db, email, password)

    if not user:
        return None

    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }