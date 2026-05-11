from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.dependencies import get_db
from services.auth.bankid import collect_bankid_status, initiate_bankid_auth
from services.auth.schemas import (
    BankIDInitiateResponse,
    BankIDLoginResponse,
    LoginResponse,
    Token,
    TwoFactorLoginRequest,
    TwoFactorSetupResponse,
    TwoFactorStatusResponse,
    TwoFactorVerifyRequest,
    UserCreate,
    UserLogin,
    UserProfileUpdate,
    UserResponse,
)
from services.auth.service import (
    complete_two_factor_login,
    disable_two_factor,
    enable_two_factor,
    get_current_user_from_token,
    get_two_factor_status,
    handle_completed_bankid_login,
    login_user,
    register_user,
    setup_two_factor,
    update_user_profile,
)

router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    return get_current_user_from_token(db, token)


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        user = register_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=LoginResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    result = login_user(db, user_data.email, user_data.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return result


@router.post("/login/2fa", response_model=Token)
def login_with_two_factor(
    body: TwoFactorLoginRequest,
    db: Session = Depends(get_db),
):
    return complete_two_factor_login(
        db=db,
        temp_token=body.temp_token,
        code=body.code,
    )


@router.get("/me", response_model=UserResponse)
def get_me(user=Depends(get_current_user)):
    return user


@router.patch("/me/profile", response_model=UserResponse)
def update_me_profile(
    profile_data: UserProfileUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_user = update_user_profile(
        db=db,
        user=user,
        profile_data=profile_data,
    )

    return updated_user


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return setup_two_factor(db=db, user=user)


@router.post("/2fa/enable", response_model=UserResponse)
def enable_2fa(
    body: TwoFactorVerifyRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return enable_two_factor(
        db=db,
        user=user,
        code=body.code,
    )


@router.post("/2fa/disable", response_model=UserResponse)
def disable_2fa(
    body: TwoFactorVerifyRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return disable_two_factor(
        db=db,
        user=user,
        code=body.code,
    )


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
def two_factor_status(user=Depends(get_current_user)):
    return get_two_factor_status(user)


@router.post("/bankid/initiate", response_model=BankIDInitiateResponse)
async def bankid_initiate():
    result = await initiate_bankid_auth()
    return result


@router.get("/bankid/status/{order_ref}", response_model=BankIDLoginResponse)
async def bankid_status(order_ref: str, db: Session = Depends(get_db)):
    result = await collect_bankid_status(order_ref)

    if result.get("status") != "complete":
        return {
            "status": result.get("status"),
            "hintCode": result.get("hintCode"),
            "orderRef": result.get("orderRef"),
            "completionData": result.get("completionData"),
            "errorCode": result.get("errorCode"),
            "details": result.get("details"),
        }

    completion_data = result.get("completionData", {})
    user_data = completion_data.get("user", {})

    personal_number = user_data.get("personalNumber")
    full_name = user_data.get("name")

    if not personal_number:
        raise HTTPException(
            status_code=500,
            detail="BankID completed but no personal number was returned",
        )

    login_result = handle_completed_bankid_login(
        db=db,
        personal_number=personal_number,
        full_name=full_name,
    )

    return {
        "status": result.get("status"),
        "hintCode": result.get("hintCode"),
        "orderRef": result.get("orderRef"),
        "completionData": completion_data,
        "access_token": login_result["access_token"],
        "token_type": login_result["token_type"],
        "user": login_result["user"],
    }