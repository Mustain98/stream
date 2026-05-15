from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

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
from services.dashboard_service import build_user_dashboard

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(user: UserCreate, session: Session = Depends(get_session)):
    existing_username = session.exec(
        select(User).where(User.username == user.username)
    ).first()

    if existing_username:
        raise HTTPException(status_code=400, detail="User already exists")

    if user.email:
        email = user.email.strip().lower()

        existing_email = session.exec(
            select(User).where(User.email == email)
        ).first()

        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
    else:
        email = None

    new_user = User(
        username=user.username,
        email=email,
        password_hash=hash_password(user.password),
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    token = create_access_token({"sub": new_user.id})

    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(user: UserLogin, session: Session = Depends(get_session)):
    db_user = session.exec(
        select(User).where(User.username == user.username)
    ).first()

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

        existing_username = session.exec(
            select(User).where(
                User.username == username,
                User.id != user.id,
            )
        ).first()

        if existing_username:
            raise HTTPException(status_code=400, detail="Username already exists")

        user.username = username

    if payload.email is not None:
        email = payload.email.strip().lower()

        if email == "":
            user.email = None
        else:
            existing_email = session.exec(
                select(User).where(
                    User.email == email,
                    User.id != user.id,
                )
            ).first()

            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")

            user.email = email

    session.add(user)
    session.commit()
    session.refresh(user)

    return user
