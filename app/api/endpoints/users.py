from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.core.security import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/users", tags=["users"])
bearer_scheme = HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Checks the token from request header
    Returns the logged in user
    """
    # decode the token and get user_id
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # fetch user from database
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns profile of the currently logged in user
    """
    return {
        "id": current_user.id,
        "display_name": current_user.display_name,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "location": current_user.location,
    }