from unittest.mock import AsyncMock, patch

MOCK_CONCERTS = [
    {
        "id": "event_001",
        "name": "Rock Night",
        "url": "https://ticketmaster.com/event/001",
        "artist": "Artist One",
        "date": "2026-09-01",
        "venue": "Main Stage",
        "city": "Warsaw",
        "country": "PL",
        "lat": 52.2297,
        "lng": 21.0122,
        "image": "https://example.com/concert.jpg",
    }
]

MOCK_ARTISTS = [
    {"id": "art1", "name": "Artist One", "genres": ["rock"], "image_url": None},
]

MOCK_CIRCLE_ARTISTS = [
    {
        "id": "art1",
        "name": "Artist One",
        "genres": ["rock"],
        "image_url": None,
        "match_info": {
            "type": "shared",
            "liked_by_user_ids": [1, 2],
            "liked_by_count": 2,
            "liked_by_all": True,
        },
    }
]


class TestSearchConcerts:

    async def test_returns_results(self, client, auth_headers):
        with patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=AsyncMock(return_value=MOCK_CONCERTS)):
            response = await client.get("/api/v1/concerts/search?artists=Artist+One", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["artist"] == "Artist One"

    async def test_pipe_separates_artists(self, client, auth_headers):
        mock = AsyncMock(return_value=MOCK_CONCERTS)
        with patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=mock):
            await client.get(
                "/api/v1/concerts/search?artists=Artist+One|Artist+Two",
                headers=auth_headers,
            )
        called_artists = mock.call_args.args[0]
        assert "Artist One" in called_artists
        assert "Artist Two" in called_artists

    async def test_with_country_filter(self, client, auth_headers):
        mock = AsyncMock(return_value=MOCK_CONCERTS)
        with patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=mock):
            await client.get(
                "/api/v1/concerts/search?artists=Artist+One&country_code=PL",
                headers=auth_headers,
            )
        assert mock.call_args.args[1] == "PL"

    async def test_requires_auth(self, client):
        response = await client.get("/api/v1/concerts/search?artists=AnyArtist")
        assert response.status_code == 401


class TestMyConcerts:

    async def test_for_you_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.concerts.recommendation_service.get_for_you_artists", new=AsyncMock(return_value=MOCK_ARTISTS)), \
             patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=AsyncMock(return_value=MOCK_CONCERTS)):
            response = await client.get("/api/v1/concerts/me/for-you", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_something_new_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.concerts.recommendation_service.get_discovery_artists", new=AsyncMock(return_value=MOCK_ARTISTS)), \
             patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=AsyncMock(return_value=MOCK_CONCERTS)):
            response = await client.get("/api/v1/concerts/me/something-new", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestCircleConcerts:

    async def test_for_you_with_two_members(self, client, two_member_circle, auth_headers):
        with patch("app.api.endpoints.concerts.recommendation_service.get_circle_for_you_artists", new=AsyncMock(return_value=MOCK_CIRCLE_ARTISTS)), \
             patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=AsyncMock(return_value=MOCK_CONCERTS)):
            response = await client.get(
                f"/api/v1/concerts/circle/{two_member_circle.id}/for-you",
                headers=auth_headers,
            )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_for_you_includes_taste_match(self, client, two_member_circle, auth_headers):
        with patch("app.api.endpoints.concerts.recommendation_service.get_circle_for_you_artists", new=AsyncMock(return_value=MOCK_CIRCLE_ARTISTS)), \
             patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=AsyncMock(return_value=MOCK_CONCERTS)):
            response = await client.get(
                f"/api/v1/concerts/circle/{two_member_circle.id}/for-you",
                headers=auth_headers,
            )
        assert "taste_match" in response.json()[0]

    async def test_for_you_needs_multiple_members(self, client, test_circle, auth_headers):
        response = await client.get(
            f"/api/v1/concerts/circle/{test_circle.id}/for-you",
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_for_you_requires_membership(self, client, test_circle, second_auth_headers):
        response = await client.get(
            f"/api/v1/concerts/circle/{test_circle.id}/for-you",
            headers=second_auth_headers,
        )
        assert response.status_code == 403

    async def test_something_new_with_two_members(self, client, two_member_circle, auth_headers):
        with patch("app.api.endpoints.concerts.recommendation_service.get_circle_discovery_artists", new=AsyncMock(return_value=MOCK_ARTISTS)), \
             patch("app.api.endpoints.concerts.ticketmaster_service.get_concerts_for_artists", new=AsyncMock(return_value=MOCK_CONCERTS)):
            response = await client.get(
                f"/api/v1/concerts/circle/{two_member_circle.id}/something-new",
                headers=auth_headers,
            )
        assert response.status_code == 200

    async def test_something_new_needs_multiple_members(self, client, test_circle, auth_headers):
        response = await client.get(
            f"/api/v1/concerts/circle/{test_circle.id}/something-new",
            headers=auth_headers,
        )
        assert response.status_code == 409
