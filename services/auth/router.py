from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.dependencies import get_db
from services.auth.schemas import UserCreate, UserLogin, UserResponse, Token
from services.auth.service import (
    authenticate_user,
    get_current_user_from_token,
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

@router.post("/bankid/initiate")
async def bankid_initiate():
    result = await initiate_bankid_auth()
    return result


@router.get("/bankid/status/{order_ref}")
async def bankid_status(order_ref: str):
    result = await collect_bankid_status(order_ref)
    return result