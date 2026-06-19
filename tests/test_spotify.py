from unittest.mock import AsyncMock, patch

MOCK_ARTISTS = [
    {"id": "art1", "name": "Artist One", "genres": ["rock", "indie"], "image_url": "https://example.com/1.jpg"},
    {"id": "art2", "name": "Artist Two", "genres": ["pop"], "image_url": None},
]

MOCK_TRACKS = [
    {"id": "trk1", "name": "Track One", "artist": "Artist One", "album": "Album A", "image_url": None},
    {"id": "trk2", "name": "Track Two", "artist": "Artist Two", "album": "Album B", "image_url": None},
]

MOCK_GENRES = ["rock", "indie", "pop", "alternative"]


class TestTopArtists:

    async def test_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.spotify.spotify_service.get_top_artists", new=AsyncMock(return_value=MOCK_ARTISTS)):
            response = await client.get("/api/v1/spotify/me/top-artists", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Artist One"

    async def test_passes_params(self, client, auth_headers):
        mock = AsyncMock(return_value=MOCK_ARTISTS)
        with patch("app.api.endpoints.spotify.spotify_service.get_top_artists", new=mock):
            await client.get(
                "/api/v1/spotify/me/top-artists?time_range=short_term&limit=5",
                headers=auth_headers,
            )
        assert mock.call_args.kwargs["time_range"] == "short_term"
        assert mock.call_args.kwargs["limit"] == 5

    async def test_requires_auth(self, client):
        response = await client.get("/api/v1/spotify/me/top-artists")
        assert response.status_code == 401


class TestTopTracks:

    async def test_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.spotify.spotify_service.get_top_tracks", new=AsyncMock(return_value=MOCK_TRACKS)):
            response = await client.get("/api/v1/spotify/me/top-tracks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Track One"

    async def test_requires_auth(self, client):
        response = await client.get("/api/v1/spotify/me/top-tracks")
        assert response.status_code == 401


class TestTopGenres:

    async def test_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.spotify.spotify_service.get_top_genres", new=AsyncMock(return_value=MOCK_GENRES)):
            response = await client.get("/api/v1/spotify/me/top-genres", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "rock" in data
        assert "pop" in data

    async def test_requires_auth(self, client):
        response = await client.get("/api/v1/spotify/me/top-genres")
        assert response.status_code == 401
