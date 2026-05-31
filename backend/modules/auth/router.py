from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from db.session import get_session
from models import User
from core.security import (
    hash_password,
    verify_password,
    needs_password_rehash,
    create_access_token,
    get_current_user,
)
from schemas.auth_schema import UserCreate, UserLogin, UserPublic, UserUpdate
from modules.auth.dashboard_service import build_user_dashboard
from modules.auth.user_service import get_user_by_username, get_user_by_email, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(user: UserCreate, session: Session = Depends(get_session)):
    if get_user_by_username(session, user.username):
        raise HTTPException(status_code=400, detail="User already exists")

    email = user.email.strip().lower() if user.email else None
    
    if email and get_user_by_email(session, email):
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = create_user(
        session=session,
        username=user.username,
        email=email,
        password_hash=hash_password(user.password),
    )

    token = create_access_token({"sub": new_user.id})

    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(user: UserLogin, session: Session = Depends(get_session)):
    db_user = get_user_by_username(session, user.username)

    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if needs_password_rehash(db_user.password_hash):
        db_user.password_hash = hash_password(user.password)
        session.add(db_user)
        session.commit()

    token = create_access_token({"sub": db_user.id})

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/dashboard")
def dashboard(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return build_user_dashboard(
        session=session,
        user=user,
    )


@router.patch("/me", response_model=UserPublic)
def update_me(
    payload: UserUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if payload.username is not None:
        username = payload.username.strip()

        if username == "":
            raise HTTPException(status_code=400, detail="Username cannot be empty")

        if get_user_by_username(session, username, exclude_id=user.id):
            raise HTTPException(status_code=400, detail="Username already exists")

        user.username = username

    if payload.email is not None:
        email = payload.email.strip().lower()

        if email == "":
            user.email = None
        else:
            if get_user_by_email(session, email, exclude_id=user.id):
                raise HTTPException(status_code=400, detail="Email already exists")

            user.email = email

    session.add(user)
    session.commit()
    session.refresh(user)

    return user
