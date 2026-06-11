from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.endpoints.users import get_current_user
from app.core.database import get_db
from app.models.circle import CircleUser
from app.models.user import User
from app.services import recommendation_service, ticketmaster_service
router = APIRouter(prefix="/concerts", tags=["concerts"])


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


def get_artist_names(artists: list[dict], limit: int) -> list[str]:
    """
    Extracts artist names and limits how many Ticketmaster searches we run
    """
    if not 1 <= limit <= 50:
        limit = 30
    return [artist["name"] for artist in artists[:limit] if artist.get("name")]


def normalize_artist_name(name: str | None) -> str:
    return (name or "").strip().lower()


def build_taste_match(artist: dict, user_names: dict[int, str]) -> dict | None:
    match_info = artist.get("match_info") or {}
    liked_by_user_ids = match_info.get("liked_by_user_ids") or []

    if not liked_by_user_ids:
        return None

    return {
        "type": match_info.get("type"),
        "liked_by_count": match_info.get("liked_by_count", len(liked_by_user_ids)),
        "liked_by_user_ids": liked_by_user_ids,
        "liked_by_display_names": [
            user_names.get(user_id, f"User {user_id}") for user_id in liked_by_user_ids
        ],
        "liked_by_all": match_info.get("liked_by_all", False),
    }


async def attach_taste_matches(
    concerts: list[dict],
    artists: list[dict],
    current_user: User,
    db: AsyncSession,
) -> list[dict]:
    """
    Adds circle taste ownership info to concerts matched by artist name.
    """
    user_ids = {
        user_id
        for artist in artists
        for user_id in (artist.get("match_info") or {}).get("liked_by_user_ids", [])
    }

    user_names: dict[int, str] = {}
    if user_ids:
        users = await db.scalars(select(User).where(User.id.in_(user_ids)))
        user_names = {
            user.id: "you" if user.id == current_user.id else user.display_name or user.email or f"User {user.id}"
            for user in users
        }

    artist_matches = {
        normalize_artist_name(artist.get("name")): build_taste_match(artist, user_names)
        for artist in artists
        if artist.get("name")
    }

    return [
        {
            **concert,
            "taste_match": artist_matches.get(normalize_artist_name(concert.get("artist"))),
        }
        for concert in concerts
    ]


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
    artist_list = [a.strip() for a in artists.split("|") if a.strip()]
    return await ticketmaster_service.get_concerts_for_artists(artist_list, country_code)


@router.get("/me/for-you")
async def get_my_for_you_concerts(
    country_code: str | None = None,
    artist_limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns upcoming concerts for user's For You artists
    """
    artists = await recommendation_service.get_for_you_artists(current_user, db)
    artist_names = get_artist_names(artists, artist_limit)
    return await ticketmaster_service.get_concerts_for_artists(artist_names, country_code)


@router.get("/me/something-new")
async def get_my_something_new_concerts(
    country_code: str | None = None,
    artist_limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns upcoming concerts for user's Something New artists
    """
    artists = await recommendation_service.get_discovery_artists(current_user, db)
    artist_names = get_artist_names(artists, artist_limit)
    return await ticketmaster_service.get_concerts_for_artists(artist_names, country_code)


@router.get("/circle/{circle_id}/for-you")
async def get_circle_for_you_concerts(
    circle_id: int,
    country_code: str | None = None,
    artist_limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns upcoming concerts for Circle For You artists
    """
    await check_circle(circle_id, current_user, db)
    artists = await recommendation_service.get_circle_for_you_artists(circle_id, db)
    selected_artists = [
        artist for artist in artists[:artist_limit if 1 <= artist_limit <= 50 else 30]
        if artist.get("name")
    ]
    artist_names = [artist["name"] for artist in selected_artists]
    concerts = await ticketmaster_service.get_concerts_for_artists(artist_names, country_code)
    return await attach_taste_matches(concerts, selected_artists, current_user, db)


@router.get("/circle/{circle_id}/something-new")
async def get_circle_something_new_concerts(
    circle_id: int,
    country_code: str | None = None,
    artist_limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns upcoming concerts for Circle Something New artists
    """
    await check_circle(circle_id, current_user, db)
    artists = await recommendation_service.get_circle_discovery_artists(circle_id, current_user, db)
    artist_names = get_artist_names(artists, artist_limit)
    return await ticketmaster_service.get_concerts_for_artists(artist_names, country_code)

