from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.endpoints.users import get_current_user
from app.models.user import User
from app.services import circle_taste_service, recommendation_service
from fastapi import HTTPException
from sqlalchemy import select, func
from app.models.circle import CircleUser

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


async def check_circle(circle_id: int, current_user: User, db: AsyncSession) -> None:
    """
    Checks if user is a member of the circle and if circle has at least 2 members
    Raises 403 if not a member or 409 if not enough members
    """
    membership = await db.scalar(
        select(CircleUser).where(
            CircleUser.circle_id == circle_id,
            CircleUser.user_id == current_user.id
        )
    )
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this circle")

    member_count = await db.scalar(
        select(func.count()).where(CircleUser.circle_id == circle_id)
    )
    if member_count < 2:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "not_enough_members",
                "message": "Waiting for at least one more person to join",
                "member_count": member_count,
                "min_required": 2,
            }
        )

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
    Artists are split into shared, partial and personal groups
    Only accessible by circle members
    Requires at least 2 members in the circle
    """
    await check_circle(circle_id, current_user, db)
    return await recommendation_service.get_circle_for_you_artists(circle_id, db)


@router.get("/circle/{circle_id}/something-new/artists")
async def get_circle_discovery_artists(
    circle_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns discovery artists for a circle
    Only accessible by circle members
    Requires at least 2 members
    """
    await check_circle(circle_id, current_user, db)
    return await recommendation_service.get_circle_discovery_artists(circle_id, current_user, db)


@router.get("/circle/{circle_id}/taste")
async def get_circle_taste(
    circle_id: int,
    time_range: str = "medium_term",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the circle's taste blend: match scores, shared artists, tracks and genres,
    and the artists only one member brings
    """
    await check_circle(circle_id, current_user, db)
    return await circle_taste_service.get_circle_taste(circle_id, current_user, db, time_range=time_range)
