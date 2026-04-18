from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    auth_provider = Column(String, nullable=False, default="local")
    bankid_personal_number = Column(String, unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))