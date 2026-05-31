from sqlmodel import Session, select
from models import User


def get_user_by_username(session: Session, username: str, exclude_id: str | None = None) -> User | None:
    query = select(User).where(User.username == username)
    if exclude_id:
        query = query.where(User.id != exclude_id)
    return session.exec(query).first()


def get_user_by_email(session: Session, email: str, exclude_id: str | None = None) -> User | None:
    query = select(User).where(User.email == email)
    if exclude_id:
        query = query.where(User.id != exclude_id)
    return session.exec(query).first()


def create_user(session: Session, username: str, email: str | None, password_hash: str) -> User:
    new_user = User(
        username=username,
        email=email,
        password_hash=password_hash,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user
