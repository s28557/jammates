from unittest.mock import AsyncMock, patch

# Mock Spotify artist response
MOCK_ARTISTS = [
    {"id": "art1", "name": "Artist One", "genres": ["rock", "indie"], "image_url": "https://example.com/1.jpg"},
    {"id": "art2", "name": "Artist Two", "genres": ["pop"], "image_url": None},
]

# Mock Spotify track response
MOCK_TRACKS = [
    {"id": "trk1", "name": "Track One", "artist": "Artist One", "album": "Album A", "image_url": None},
    {"id": "trk2", "name": "Track Two", "artist": "Artist Two", "album": "Album B", "image_url": None},
]

# Mock derived genre response
MOCK_GENRES = ["rock", "indie", "pop", "alternative"]


# Top artists endpoint tests
class TestTopArtists:

    async def test_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.spotify.spotify_service.get_top_artists", new=AsyncMock(return_value=MOCK_ARTISTS)):
            response = await client.get("/api/v1/spotify/me/top-artists", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Artist One"

    async def test_passes_params(self, client, auth_headers):
        # query params should pass through to the Spotify service
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


# Top tracks endpoint tests
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


# Top genres endpoint tests
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


# Taste endpoint tests
class TestTaste:

    async def test_returns_profile(self, client, auth_headers):
        profile = {"artists": MOCK_ARTISTS, "tracks": MOCK_TRACKS, "albums": [], "genres": []}
        mock = AsyncMock(return_value=profile)
        with patch("app.api.endpoints.spotify.spotify_service.get_taste_profile", new=mock):
            response = await client.get("/api/v1/spotify/me/taste?time_range=long_term", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["artists"][0]["name"] == "Artist One"
        assert mock.call_args.kwargs["time_range"] == "long_term"

    async def test_requires_auth(self, client):
        response = await client.get("/api/v1/spotify/me/taste")
        assert response.status_code == 401


# Taste helpers tests
class TestTasteHelpers:

    def test_albums_rank_by_track_count_then_best_position(self):
        from app.services.spotify_service import get_top_albums

        tracks = [
            {"album_id": "a", "album": "A", "artist": "X", "image_url": None},
            {"album_id": "b", "album": "B", "artist": "Y", "image_url": None},
            {"album_id": "c", "album": "C", "artist": "Z", "image_url": None},
            {"album_id": "b", "album": "B", "artist": "Y", "image_url": None},
            {"album_id": None, "album": "No id", "artist": "Q", "image_url": None},
        ]
        albums = get_top_albums(tracks)
        assert [album["id"] for album in albums] == ["b", "a", "c"]
        assert albums[0]["track_count"] == 2
        assert "best_rank" not in albums[0]

    def test_genres_weight_higher_ranked_artists(self):
        from app.services.spotify_service import get_weighted_genres

        artists = [
            {"genres": ["rock"]},
            {"genres": ["pop"]},
            {"genres": []},
        ]
        genres = get_weighted_genres(artists)
        assert genres[0] == {"name": "rock", "score": 1.0}
        assert genres[1]["name"] == "pop"
        assert genres[1]["score"] < 1.0

    def test_genres_empty_when_no_artist_has_genres(self):
        from app.services.spotify_service import get_weighted_genres

        assert get_weighted_genres([{"genres": []}]) == []
