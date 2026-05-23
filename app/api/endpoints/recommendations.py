from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.endpoints.users import get_current_user
from app.models.user import User
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/me/something-new/artists")
async def get_discovery_artists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
       Returns artists the user might not know yet - used for Something New? feature
    """
    artists = await recommendation_service.get_discovery_artists(current_user, db)
    return artists