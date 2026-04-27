from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    home_address: str | None = None
    home_lat: float | None = None
    home_lon: float | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    created_at: datetime
    home_address: str | None = None
    home_lat: float | None = None
    home_lon: float | None = None

    model_config = {
        "from_attributes": True
    }


class Token(BaseModel):
    access_token: str
    token_type: str


class BankIDInitiateResponse(BaseModel):
    orderRef: str
    autoStartToken: str
    qrStartToken: str
    qrStartSecret: str


class BankIDStatusResponse(BaseModel):
    orderRef: str | None = None
    status: str
    hintCode: str | None = None
    completionData: dict | None = None
    errorCode: str | None = None
    details: str | None = None


class BankIDLoginResponse(BaseModel):
    status: str
    hintCode: str | None = None
    access_token: str | None = None
    token_type: str | None = None
    user: UserResponse | None = None
    orderRef: str | None = None
    completionData: dict | None = None
    errorCode: str | None = None
    details: str | None = None


class BankIDInitiateRequest(BaseModel):
    personal_number: str | None = None