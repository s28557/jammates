import spotipy
from app.models.user import User
from spotipy.exceptions import SpotifyException
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from spotipy.oauth2 import SpotifyOAuth
from app.core.config import settings
import asyncio
import logging
from fastapi import HTTPException
logger = logging.getLogger(__name__)

async def refresh_token_if_needed(user: User, db: AsyncSession) -> User:
    """
    Checks if access token is expired and refreshes if needed
    Called before any Spotify API request
    """
    now = datetime.now(timezone.utc)
    expires_at = user.token_expires_at # handle timezone-naive datetime from db
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at > now:
        return user  # token still valid

    # if token expired -> refreshes
    oauth = SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    )

    try:
        token_info = await asyncio.to_thread(oauth.refresh_access_token, user.refresh_token)
    except Exception as e:
        logger.error(f"Failed to refresh Spotify token: {e}")
        raise

    user.access_token = token_info["access_token"]
    user.token_expires_at = datetime.fromtimestamp(token_info["expires_at"], tz=timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user


# time_range options: short_term (4 weeks), medium_term (6 months), long_term (years) !

def get_spotify_client(user: User) -> spotipy.Spotify:
    """
    Creates Spotify client using user's stored access token
    """
    return spotipy.Spotify(auth=user.access_token)

async def get_top_artists(user: User, db: AsyncSession, limit: int = 20, time_range: str = "medium_term") -> list[dict]:
    """
    Gets user's top artists from Spotify
    """
    user = await refresh_token_if_needed(user, db)  # refresh token if expired

    if time_range not in ("short_term", "medium_term", "long_term"):
        time_range = "medium_term"
    if not 1 <= limit <= 50:
        limit = 20

    try:
        sp = get_spotify_client(user)
        result = await asyncio.to_thread(sp.current_user_top_artists, limit=limit, time_range=time_range)
        return result.get("items", [])
    except SpotifyException as e:
        # token expired or invalid
        logger.error(f"Spotify error while fetching top artists: {e}")
        return []

async def get_top_tracks(user: User, db: AsyncSession, limit: int = 20, time_range: str = "medium_term") -> list[dict]:
    """
    Gets user's top tracks from Spotify
    """
    user = await refresh_token_if_needed(user, db)
    if time_range not in ("short_term", "medium_term", "long_term"):
        time_range = "medium_term"
    if not 1 <= limit <= 50:
        limit = 20

    try:
        sp = get_spotify_client(user)
        result = await asyncio.to_thread(sp.current_user_top_tracks, limit=limit, time_range=time_range)
        return result.get("items", [])
    except SpotifyException as e:
        logger.error(f"Spotify error while fetching top tracks: {e}")
        return []

async def get_top_genres(user: User, db: AsyncSession, limit: int = 20) -> list[str]:
    """
    Gets top genres from user's top artists
    Spotify doesn't have a direct genres endpoint so we derive it from artists
    """
    artists = await get_top_artists(user, db, limit=limit)
    genre_counts: dict[str, int] = {}
    for artist in artists:
        for genre in artist.get("genres", []):
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
    return sorted(genre_counts, key=genre_counts.get, reverse=True)



async def get_followed_artists(user: User, db: AsyncSession) -> list[dict]:
    """
    Gets artists that the user follows on Spotify
    """
    user = await refresh_token_if_needed(user, db)
    try:
        sp = get_spotify_client(user)
        result = await asyncio.to_thread(sp.current_user_followed_artists, limit=50)
        return result.get("artists", {}).get("items", [])
    except SpotifyException as e:
        if e.http_status == 403:
            raise HTTPException(
                status_code=403,
                detail="Spotify permissions missing. Please reconnect Spotify"
            )
        logger.error(f"Spotify error while fetching followed artists: {e}")
        return []

async def get_recently_played_artists(user: User, db: AsyncSession) -> list[dict]:
    """
    Gets artists from user's recently played tracks
    Extracts unique artists from recently played tracks
    """
    user = await refresh_token_if_needed(user, db)
    try:
        sp = get_spotify_client(user)
        result = await asyncio.to_thread(sp.current_user_recently_played, limit=50)

        # extract unique artists from tracks
        seen_ids = set()
        artists = []
        for item in result.get("items", []):
            for artist in item["track"]["artists"]:
                if artist["id"] not in seen_ids:
                    seen_ids.add(artist["id"])
                    artists.append(artist)
        return artists
    except SpotifyException as e:
        if e.http_status == 403:
            raise HTTPException(
                status_code=403,
                detail="Spotify permissions missing. Please reconnect Spotify"
            )
        logger.error(f"Spotify error while fetching recently played artists: {e}")
        return []

async def get_something_new(user: User, db: AsyncSession) -> list[dict]:
    """
    Returns artists the user might not know yet
    Sources: recently played, followed artists, long-term top artists
    Removes current top artists (medium_term) from all sources
    """
    user = await refresh_token_if_needed(user, db)
    # get top artists - what user listens to right now
    medium_term = await get_top_artists(user, db, time_range="medium_term")
    known_ids = {a["id"] for a in medium_term}

    # source 1: recently played -> remove top artists
    recently_played = await get_recently_played_artists(user, db)
    source1 = [a for a in recently_played if a["id"] not in known_ids]

    # source 2: followed artists -> remove top artists
    followed = await get_followed_artists(user, db)
    source2 = [a for a in followed if a["id"] not in known_ids]

    # source 3: long-term top artists -> remove top artists
    long_term = await get_top_artists(user, db, time_range="long_term")
    source3 = [a for a in long_term if a["id"] not in known_ids]

    # combine all sources and remove duplicates
    seen_ids = set()
    unique_new = []
    for artist in source1 + source2 + source3:
        if artist["id"] not in seen_ids:
            seen_ids.add(artist["id"])
            unique_new.append(artist)

    return unique_new