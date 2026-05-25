from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.endpoints.users import get_current_user
from app.models.user import User
from app.services import recommendation_service
from fastapi import HTTPException
from sqlalchemy import select
from app.models.circle import CircleUser

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/me/for-you-artists")
async def get_for_you_artists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns "for you" artists recommendations based on user's listening history
    """
    return await recommendation_service.get_for_you_artists(current_user, db)

@router.get("/me/something-new/artists")
async def get_discovery_artists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
       Returns artists the user might not know yet - used for Something New?
    """
    artists = await recommendation_service.get_discovery_artists(current_user, db)
    return artists

@router.get("/circle/{circle_id}/for-you")
async def get_circle_for_you_artists(
    circle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns artist recommendations for a circle based on shared music taste
    Only accessible by circle members
    """
    # verify user is a member of this circle
    membership = await db.scalar(
        select(CircleUser).where(
            CircleUser.circle_id == circle_id,
            CircleUser.user_id == current_user.id
        )
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this circle")

    return await recommendation_service.get_circle_for_you_artists(circle_id, db)