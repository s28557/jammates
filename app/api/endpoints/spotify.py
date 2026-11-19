from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.endpoints.users import get_current_user
from app.models.user import User
from app.services import spotify_service

router = APIRouter(prefix="/spotify", tags=["spotify"])

@router.get("/me/top-artists")
async def get_my_top_artists(
    time_range: str = "medium_term",
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns current user's top artists from Spotify
    """
    return await spotify_service.get_top_artists(current_user, db, limit=limit, time_range=time_range)


@router.get("/me/top-tracks")
async def get_my_top_tracks(
    time_range: str = "medium_term",
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns current user's top tracks from Spotify
    """
    return await spotify_service.get_top_tracks(current_user, db, limit=limit, time_range=time_range)


@router.get("/me/top-genres")
async def get_my_top_genres(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns current user's top genres derived from top artists
    """
    return await spotify_service.get_top_genres(current_user, db)


@router.get("/me/taste")
async def get_my_taste(
    time_range: str = "medium_term",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns current user's top artists, tracks, albums and genres for one time range
    """
    return await spotify_service.get_taste_profile(current_user, db, time_range=time_range)
