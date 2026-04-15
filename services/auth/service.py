from sqlalchemy.orm import Session

from services.auth.models import User
from services.auth.repository import create_user, get_user_by_email
from services.auth.schemas import UserCreate
from services.auth.security import verify_password


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