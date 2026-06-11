from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator
from app.core.config import settings
from jose import jwt, JWTError


class EncryptedString(TypeDecorator):
    """Transparently encrypts/decrypts string columns using Fernet symmetric encryption."""
    impl = String
    cache_ok = True

    def _fernet(self) -> Fernet:
        return Fernet(settings.ENCRYPTION_KEY.encode())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return self._fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self._fernet().decrypt(value.encode()).decode()

def create_access_token(user_id: int) -> str:
    """
    Creates a JWT access token for user
    Token expires after 30 minutes
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {
        "sub": str(user_id),  # who is this token for
        "exp": expire,  # when does it expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256") # token created

def decode_access_token(token: str) -> int | None:
    """
    Decodes created JWT token and returns user id
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"])
    except JWTError as e:
        print(f"Token decode failed: {e}")
        return None # token expired or invalid