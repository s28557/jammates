from fastapi import APIRouter
from fastapi.responses import RedirectResponse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from app.core.config import settings
from app.models.user import User
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from datetime import datetime, timezone
from app.core.security import create_access_token
from spotipy.cache_handler import MemoryCacheHandler
from urllib.parse import urlencode

router = APIRouter(prefix="/auth", tags=["auth"]) # container for endpoints

def get_spotify_oauth():
    """
    Creates Spotify OAuth session
    The app wants access to:
    user-top-read - users top artists and tracks
    user-read-private - users profile
    user-read-email - users email
    user-follow-read - users followed artists
    user-read-recently-played - users recently played tracks
    """
    return SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
        scope="user-top-read user-read-private user-read-email user-follow-read user-read-recently-played",
        cache_handler=MemoryCacheHandler(),  # don't cache tokens to disk
    )

@router.get("/spotify/login")
async def spotify_login():
    """
    Generates link to Spotify login page and redirects user there
    """
    oauth = get_spotify_oauth()
    auth_url = oauth.get_authorize_url()
    return RedirectResponse(url=auth_url)

@router.get("/spotify/callback")
async def spotify_callback(code: str, db: AsyncSession = Depends(get_db)):
    """
    Handles Spotify OAuth callback
    Exchanges the one-time code for tokens
    Gets user's Spotify profile
    Creates/Updates user's account in database
    """
    # spotify sends one-time code, we exchange it for tokens
    oauth = get_spotify_oauth()
    token_info = oauth.get_access_token(code)

    sp = spotipy.Spotify(auth=token_info["access_token"])
    spotify_user = sp.current_user() # who logged in
    images = spotify_user.get("images", [])
    avatar = images[0].get("url") if images else None # profile pic

    #check if new user
    user = await db.scalar(
        select(User).where(User.spotify_id == spotify_user["id"])
    )
    if user:
        # refresh tokens
        user.access_token = token_info["access_token"]
        user.refresh_token = token_info.get("refresh_token") or user.refresh_token
        user.token_expires_at = datetime.fromtimestamp(token_info["expires_at"], tz=timezone.utc)

    else:
        # first time -> create account
        user = User(
            spotify_id=spotify_user["id"],
            email=spotify_user.get("email", ""),
            display_name=spotify_user.get("display_name", ""),
            avatar_url=avatar,
            access_token=token_info["access_token"],
            refresh_token=token_info.get("refresh_token", ""),
            token_expires_at=datetime.fromtimestamp(token_info["expires_at"], tz=timezone.utc),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    callback_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/callback?{urlencode({'token': token})}"
    return RedirectResponse(url=callback_url)

