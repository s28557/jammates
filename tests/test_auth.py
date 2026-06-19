from unittest.mock import patch
from sqlalchemy import select
from app.models.user import User

# Fake Spotify token returned by mocked OAuth flow
FAKE_TOKEN_INFO = {
    "access_token": "fake-spotify-access-token",
    "refresh_token": "fake-spotify-refresh-token",
    "expires_at": 9999999999,
}


# Spotify login redirect tests
class TestSpotifyLogin:

    async def test_redirects_to_spotify(self, client):
        response = await client.get("/api/v1/auth/spotify/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "accounts.spotify.com" in response.headers["location"]


# Spotify callback user creation and update tests
class TestSpotifyCallback:

    async def test_creates_new_user(self, client, db):
        # Spotify profile for a user that is not in the database yet
        fake_spotify_user = {
            "id": "brand_new_spotify_user",
            "email": "newuser@example.com",
            "display_name": "New User",
            "images": [{"url": "https://example.com/avatar.jpg"}],
        }

        with patch("app.api.endpoints.loginAuth.SpotifyOAuth") as mock_oauth_cls, \
             patch("app.api.endpoints.loginAuth.spotipy") as mock_spotipy:
            mock_oauth_cls.return_value.get_access_token.return_value = FAKE_TOKEN_INFO
            mock_spotipy.Spotify.return_value.current_user.return_value = fake_spotify_user

            response = await client.get(
                "/api/v1/auth/spotify/callback?code=test_auth_code",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "token=" in response.headers["location"]

        user = await db.scalar(select(User).where(User.spotify_id == "brand_new_spotify_user"))
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.display_name == "New User"

    async def test_updates_existing_user(self, client, db, test_user):
        fake_spotify_user = {
            "id": test_user.spotify_id,
            "email": test_user.email,
            "display_name": test_user.display_name,
            "images": [],
        }
        updated_token_info = {**FAKE_TOKEN_INFO, "access_token": "updated-access-token"}

        # mocked OAuth and Spotify API prevent external requests
        with patch("app.api.endpoints.loginAuth.SpotifyOAuth") as mock_oauth_cls, \
             patch("app.api.endpoints.loginAuth.spotipy") as mock_spotipy:
            mock_oauth_cls.return_value.get_access_token.return_value = updated_token_info
            mock_spotipy.Spotify.return_value.current_user.return_value = fake_spotify_user

            response = await client.get(
                "/api/v1/auth/spotify/callback?code=test_auth_code",
                follow_redirects=False,
            )

        assert response.status_code in (302, 307)
        assert "token=" in response.headers["location"]
