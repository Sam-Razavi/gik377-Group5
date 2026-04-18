from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.dependencies import get_db

from services.auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    BankIDInitiateResponse,
    BankIDStatusResponse,
    BankIDLoginResponse,
)

from services.auth.service import (
    authenticate_user,
    get_current_user_from_token,
    get_or_create_bankid_user,
    register_user,
)

from services.auth.security import create_access_token
from services.auth.bankid import initiate_bankid_auth, collect_bankid_status


router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        user = register_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.email, user_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    user = get_current_user_from_token(db, token)

    return user

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

    user = get_or_create_bankid_user(
        db=db,
        personal_number=personal_number,
        full_name=full_name,
    )

    access_token = create_access_token(data={"sub": user.email})

    return {
        "status": result.get("status"),
        "hintCode": result.get("hintCode"),
        "orderRef": result.get("orderRef"),
        "completionData": completion_data,
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }