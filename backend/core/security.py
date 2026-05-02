import hashlib
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlmodel import Session

from db.session import get_session
from models import User

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

password_hasher = PasswordHasher()
bearer_scheme = HTTPBearer()

# ---------- Password ----------
def normalize_password(password: str) -> str:
    """Normalize passwords before hashing to keep legacy bcrypt compatibility."""
    return hashlib.sha256(password.encode()).hexdigest()

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hasher.hash(normalize_password(password))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against either Argon2 or legacy bcrypt hashes."""
    normalized = normalize_password(plain_password)

    if hashed_password.startswith("$argon2"):
        try:
            return password_hasher.verify(hashed_password, normalized)
        except (VerifyMismatchError, InvalidHashError):
            return False

    return False


def needs_password_rehash(hashed_password: str) -> bool:
    if hashed_password.startswith("$argon2"):
        try:
            return password_hasher.check_needs_rehash(hashed_password)
        except InvalidHashError:
            return True

    return True

# ---------- JWT ----------
def create_access_token(data: dict):
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, ALGORITHM)

def decode_token(token: str):
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
    

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    token = credentials.credentials
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise creds_exc
    except JWTError:
        raise creds_exc

    user = session.get(User, user_id)
    if not user:
        raise creds_exc
    return user
