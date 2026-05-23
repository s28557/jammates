from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.endpoints.users import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services import ticketmaster_service
router = APIRouter(prefix="/concerts", tags=["concerts"])

@router.get("/search")
async def search_concerts(
    artists: str,  # pipe-separated artist names
    country_code: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search upcoming concerts for one or more artists
    artists param is separated by pipe |
    Optionally filter by country code (ISO 3166 e.g. 'PL', 'GB', 'US')
    """
    artist_list = [a.strip() for a in artists.split("|")]
    return await ticketmaster_service.get_concerts_for_artists(artist_list, country_code)