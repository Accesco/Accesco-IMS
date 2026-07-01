from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
from jose import jwt
import bcrypt
from app.core.config import settings

def get_password_hash(password: str) -> str:
    """Hashes a raw password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its hashed value."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_access_token(
    subject: Union[str, Any],
    roles: list[str],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generates a JWT access token containing the user identity (subject) and roles.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "roles": roles
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes and validates a JWT access token.
    Returns the payload dictionary if valid, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except Exception:
        return None
