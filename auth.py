from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import UserORM

# Security configuration - in a real app, these would be in environment variables
SECRET_KEY: str = "your-secret-key-for-jwt-signing"
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash.

    Args:
        plain_password: The password in plain text.
        hashed_password: The hashed version from the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a hash for a given password.

    Args:
        password: The plain text password.

    Returns:
        The hashed password string.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict[str, str], expires_delta: timedelta | None = None) -> str:
    """Create a new JWT access token.

    Args:
        data: Data to be encoded into the token.
        expires_delta: Optional expiration time delta.

    Returns:
        The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> UserORM:
    """Decode and validate the JWT token to return the current user.

    Args:
        token: The JWT token from the Authorization header.
        db: Active database session.

    Returns:
        The authenticated User record.

    Raises:
        HTTPException: 401 if the token is invalid or user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(UserORM).filter(UserORM.username == username).first()
    if user is None:
        raise credentials_exception
    return user
