from uuid import uuid4

from sqlalchemy.orm import Session

from services.auth.models import User
from services.auth.schemas import UserCreate
from services.auth.security import hash_password


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_bankid_personal_number(
    db: Session, personal_number: str
) -> User | None:
    return (
        db.query(User)
        .filter(User.bankid_personal_number == personal_number)
        .first()
    )


def create_user(db: Session, user_data: UserCreate) -> User:
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        auth_provider="local",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def create_bankid_user(
    db: Session,
    personal_number: str,
    full_name: str | None = None,
) -> User:
    synthetic_email = f"bankid_{personal_number}@example.com"
    random_password = uuid4().hex

    new_user = User(
        email=synthetic_email,
        hashed_password=hash_password(random_password),
        full_name=full_name,
        auth_provider="bankid",
        bankid_personal_number=personal_number,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user