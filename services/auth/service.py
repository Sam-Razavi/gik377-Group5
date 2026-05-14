from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.auth.models import User
from services.auth.repository import (
    create_bankid_user,
    create_user,
    get_user_by_bankid_personal_number,
    get_user_by_email,
)
from services.auth.schemas import UserCreate, UserProfileUpdate
from services.auth.security import (
    create_2fa_temp_token,
    create_access_token,
    decode_2fa_temp_token,
    decode_access_token,
    generate_2fa_secret,
    get_2fa_provisioning_uri,
    verify_2fa_code,
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

    # BankID users should not log in with email/password
    if user.auth_provider != "local":
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def login_user(db: Session, email: str, password: str) -> dict | None:
    user = authenticate_user(db, email, password)

    if not user:
        return None

    if user.two_factor_enabled:
        temp_token = create_2fa_temp_token(user.email)

        return {
            "requires_2fa": True,
            "temp_token": temp_token,
        }

    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "requires_2fa": False,
    }


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


def setup_two_factor(db: Session, user: User) -> dict:
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is only available for email/password users",
        )

    secret = generate_2fa_secret()

    user.two_factor_secret = secret
    user.two_factor_enabled = False

    db.commit()
    db.refresh(user)

    provisioning_uri = get_2fa_provisioning_uri(
        email=user.email,
        secret=secret,
    )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "message": "Scan the provisioning URI with Microsoft Authenticator or Google Authenticator, then verify the code to enable 2FA.",
    }


def enable_two_factor(db: Session, user: User, code: str) -> User:
    if user.auth_provider != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is only available for email/password users",
        )

    if not user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup has not been started",
        )

    if not verify_2fa_code(user.two_factor_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code",
        )

    user.two_factor_enabled = True

    db.commit()
    db.refresh(user)

    return user


def disable_two_factor(db: Session, user: User, code: str) -> User:
    if not user.two_factor_enabled or not user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    if not verify_2fa_code(user.two_factor_secret, code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code",
        )

    user.two_factor_enabled = False
    user.two_factor_secret = None

    db.commit()
    db.refresh(user)

    return user


def get_two_factor_status(user: User) -> dict:
    return {
        "two_factor_enabled": bool(user.two_factor_enabled),
    }


def complete_two_factor_login(
    db: Session,
    temp_token: str,
    code: str,
) -> dict:
    email = decode_2fa_temp_token(temp_token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA temporary token",
        )

    user = get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.two_factor_enabled or not user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this user",
        )

    if not verify_2fa_code(user.two_factor_secret, code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code",
        )

    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def update_user_profile(
    db: Session,
    user: User,
    profile_data: UserProfileUpdate,
) -> User:
    update_data = profile_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user