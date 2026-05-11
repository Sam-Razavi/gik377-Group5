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
    two_factor_enabled: bool = False

    model_config = {
        "from_attributes": True
    }


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    home_address: str | None = None
    home_lat: float | None = None
    home_lon: float | None = None


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    access_token: str | None = None
    token_type: str | None = None
    requires_2fa: bool = False
    temp_token: str | None = None


class TwoFactorSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    message: str


class TwoFactorVerifyRequest(BaseModel):
    code: str


class TwoFactorLoginRequest(BaseModel):
    temp_token: str
    code: str


class TwoFactorStatusResponse(BaseModel):
    two_factor_enabled: bool


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