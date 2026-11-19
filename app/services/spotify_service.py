import spotipy
from app.models.user import User
from spotipy.exceptions import SpotifyException
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from spotipy.oauth2 import SpotifyOAuth
from app.core.cache import cache_get, cache_set
from app.core.config import settings
import asyncio
import logging
from fastapi import HTTPException
logger = logging.getLogger(__name__)

# Spotify data changes slowly, so For You and Something New can share it
SPOTIFY_USER_CACHE_TTL_SECONDS = 60 * 30
SPOTIFY_RECENT_CACHE_TTL_SECONDS = 60 * 10
SPOTIFY_GENRE_CACHE_TTL_SECONDS = 60 * 60 * 24


def get_spotify_cache_key(kind: str, *parts) -> str:
    return ":".join(["spotify", "v1", kind, *(str(part) for part in parts)])

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


def map_artist(artist: dict) -> dict:
    """
    Maps raw Spotify artist data to only what we need
    """
    return {
        "id": artist["id"],
        "name": artist["name"],
        "genres": artist.get("genres", []),
        "image_url": artist.get("images", [{}])[0].get("url") if artist.get("images") else None,
    }


def map_track(track: dict) -> dict:
    """
    Maps raw Spotify track data to only what we need
    """
    album = track.get("album", {})
    return {
        "id": track["id"],
        "name": track["name"],
        "artist": track["artists"][0]["name"] if track.get("artists") else None,
        "artists": [{"id": artist["id"], "name": artist["name"]} for artist in track.get("artists", []) if artist.get("id")],
        "album": album.get("name"),
        "album_id": album.get("id"),
        "album_artist": album["artists"][0]["name"] if album.get("artists") else None,
        "image_url": album.get("images", [{}])[0].get("url") if album.get("images") else None,
    }

async def get_top_artists(user: User, db: AsyncSession, limit: int = 20, time_range: str = "medium_term") -> list[dict]:
    """
    Gets user's top artists from Spotify
    """
    if time_range not in ("short_term", "medium_term", "long_term"):
        time_range = "medium_term"
    if not 1 <= limit <= 50:
        limit = 20

    cache_key = get_spotify_cache_key("top-artists", user.id, time_range, limit)
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    user = await refresh_token_if_needed(user, db)  # refresh token if expired

    try:
        sp = get_spotify_client(user)
        result = await asyncio.to_thread(sp.current_user_top_artists, limit=limit, time_range=time_range)
        artists = [map_artist(a) for a in result.get("items", [])]
        await cache_set(cache_key, artists, ttl_seconds=SPOTIFY_USER_CACHE_TTL_SECONDS)
        return artists
    except SpotifyException as e:
        # token expired or invalid
        logger.error(f"Spotify error while fetching top artists: {e}")
        return []

async def get_top_tracks(user: User, db: AsyncSession, limit: int = 20, time_range: str = "medium_term") -> list[dict]:
    """
    Gets user's top tracks from Spotify
    """
    if time_range not in ("short_term", "medium_term", "long_term"):
        time_range = "medium_term"
    if not 1 <= limit <= 50:
        limit = 20

    # tracks-v2: cached tracks carry every artist id, older entries without them are skipped
    cache_key = get_spotify_cache_key("top-tracks-v2", user.id, time_range, limit)
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    user = await refresh_token_if_needed(user, db)

    try:
        sp = get_spotify_client(user)
        result = await asyncio.to_thread(sp.current_user_top_tracks, limit=limit, time_range=time_range)
        tracks = [map_track(t) for t in result.get("items", [])]
        await cache_set(cache_key, tracks, ttl_seconds=SPOTIFY_USER_CACHE_TTL_SECONDS)
        return tracks
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


def get_top_albums(tracks: list[dict], limit: int = 12) -> list[dict]:
    """
    Derives top albums from top tracks
    Spotify has no top albums endpoint, so albums rank by how many top tracks they hold,
    ties broken by their best track position
    """
    albums: dict[str, dict] = {}
    for rank, track in enumerate(tracks):
        album_id = track.get("album_id")
        if not album_id:
            continue
        if album_id not in albums:
            albums[album_id] = {
                "id": album_id,
                "name": track.get("album"),
                "artist": track.get("album_artist") or track.get("artist"),
                "image_url": track.get("image_url"),
                "track_count": 0,
                "best_rank": rank,
            }
        albums[album_id]["track_count"] += 1

    ranked = sorted(albums.values(), key=lambda album: (-album["track_count"], album["best_rank"]))
    return [{key: value for key, value in album.items() if key != "best_rank"} for album in ranked[:limit]]


def get_weighted_genres(artists: list[dict], limit: int = 10) -> list[dict]:
    """
    Genre shares from top artists, higher ranked artists weigh more
    Many artists come back from Spotify without genres, so this only covers the ones that have them
    """
    scores: dict[str, float] = {}
    for rank, artist in enumerate(artists):
        weight = len(artists) - rank
        for genre in artist.get("genres", []):
            scores[genre] = scores.get(genre, 0) + weight

    top = sorted(scores.items(), key=lambda item: -item[1])[:limit]
    if not top:
        return []

    highest = top[0][1]
    return [{"name": genre, "score": round(score / highest, 3)} for genre, score in top]


async def get_taste_profile(user: User, db: AsyncSession, time_range: str = "medium_term") -> dict:
    """
    Top artists, tracks, albums and genres for one time range, used by the Taste view
    """
    # refresh once up front so parallel Spotify calls never refresh concurrently
    user = await refresh_token_if_needed(user, db)
    artists, tracks = await asyncio.gather(
        get_top_artists(user, db, limit=50, time_range=time_range),
        get_top_tracks(user, db, limit=50, time_range=time_range),
    )

    return {
        "artists": artists,
        "tracks": tracks,
        "albums": get_top_albums(tracks),
        "genres": get_weighted_genres(artists),
    }



async def get_followed_artists(user: User, db: AsyncSession) -> list[dict]:
    """
    Gets artists that the user follows on Spotify
    """
    cache_key = get_spotify_cache_key("followed-artists", user.id)
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    user = await refresh_token_if_needed(user, db)
    try:
        sp = get_spotify_client(user)
        result = await asyncio.to_thread(sp.current_user_followed_artists, limit=50)
        artists = [map_artist(a) for a in result.get("artists", {}).get("items", [])]
        await cache_set(cache_key, artists, ttl_seconds=SPOTIFY_USER_CACHE_TTL_SECONDS)
        return artists
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
    cache_key = get_spotify_cache_key("recent-artists", user.id)
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

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
        await cache_set(cache_key, artists, ttl_seconds=SPOTIFY_RECENT_CACHE_TTL_SECONDS)
        return artists
    except SpotifyException as e:
        if e.http_status == 403:
            raise HTTPException(
                status_code=403,
                detail="Spotify permissions missing. Please reconnect Spotify"
            )
        logger.error(f"Spotify error while fetching recently played artists: {e}")
        return []

async def search_artists_by_genre(user: User, db: AsyncSession, genre: str, limit: int = 10) -> list[dict]:
    """
    Searches Spotify for artists by genre
    Returns a list of artists with id, name, popularity and genres
    """
    # genre results are the same for every user
    cache_key = get_spotify_cache_key("genre-artists", genre.strip().lower(), limit)
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    user = await refresh_token_if_needed(user, db)
    try:
        sp = get_spotify_client(user)
        results = await asyncio.to_thread(sp.search, q=f'genre:"{genre}"', type="artist", limit=limit)
        artists = [
            {
                "id": artist["id"],
                "name": artist["name"],
                "popularity": artist["popularity"],
                "genres": artist.get("genres", []),
                "image_url": artist.get("images", [{}])[0].get("url") if artist.get("images") else None,
            }
            for artist in results["artists"]["items"]
        ]
        await cache_set(cache_key, artists, ttl_seconds=SPOTIFY_GENRE_CACHE_TTL_SECONDS)
        return artists
    except SpotifyException as e:
        logger.error(f"Spotify error while searching artists by genre {genre}: {e}")
        return []