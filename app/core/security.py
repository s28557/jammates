from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings
from jose import jwt, JWTError

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