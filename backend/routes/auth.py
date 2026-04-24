from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from db.session import get_session
from models import User
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from schemas.auth_schema import UserCreate, UserLogin, UserPublic

router = APIRouter(prefix="/auth",tags=["auth"])


# ---------------- SIGNUP ----------------
@router.post("/signup")
def signup(user: UserCreate, session: Session = Depends(get_session)):

    existing = session.exec(
        select(User).where(User.username == user.username)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        username=user.username,
        password_hash=hash_password(user.password)
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    token = create_access_token({"sub": new_user.id})

    return {"access_token": token, "token_type": "bearer"}


# ---------------- LOGIN ----------------
@router.post("/login")
def login(user: UserLogin, session: Session = Depends(get_session)):

    db_user = session.exec(
        select(User).where(User.username == user.username)
    ).first()

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": db_user.id})

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user
