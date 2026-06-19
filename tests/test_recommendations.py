from unittest.mock import AsyncMock, patch

MOCK_ARTISTS = [
    {"id": "art1", "name": "Artist One", "genres": ["rock"], "image_url": None},
    {"id": "art2", "name": "Artist Two", "genres": ["pop"], "image_url": None},
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
    },
    {
        "id": "art2",
        "name": "Artist Two",
        "genres": ["pop"],
        "image_url": None,
        "match_info": {
            "type": "personal",
            "liked_by_user_ids": [1],
            "liked_by_count": 1,
            "liked_by_all": False,
        },
    },
]


class TestMyArtists:

    async def test_for_you_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.recommendations.recommendation_service.get_for_you_artists", new=AsyncMock(return_value=MOCK_ARTISTS)):
            response = await client.get("/api/v1/recommendations/me/for-you-artists", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Artist One"

    async def test_for_you_requires_auth(self, client):
        response = await client.get("/api/v1/recommendations/me/for-you-artists")
        assert response.status_code == 401

    async def test_discovery_returns_list(self, client, auth_headers):
        with patch("app.api.endpoints.recommendations.recommendation_service.get_discovery_artists", new=AsyncMock(return_value=MOCK_ARTISTS)):
            response = await client.get("/api/v1/recommendations/me/something-new/artists", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_discovery_requires_auth(self, client):
        response = await client.get("/api/v1/recommendations/me/something-new/artists")
        assert response.status_code == 401


class TestCircleArtists:

    async def test_for_you_with_two_members(self, client, two_member_circle, auth_headers):
        with patch("app.api.endpoints.recommendations.recommendation_service.get_circle_for_you_artists", new=AsyncMock(return_value=MOCK_CIRCLE_ARTISTS)):
            response = await client.get(
                f"/api/v1/recommendations/circle/{two_member_circle.id}/for-you",
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "match_info" in data[0]

    async def test_for_you_needs_multiple_members(self, client, test_circle, auth_headers):
        response = await client.get(
            f"/api/v1/recommendations/circle/{test_circle.id}/for-you",
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_for_you_requires_membership(self, client, test_circle, second_auth_headers):
        response = await client.get(
            f"/api/v1/recommendations/circle/{test_circle.id}/for-you",
            headers=second_auth_headers,
        )
        assert response.status_code == 403

    async def test_discovery_with_two_members(self, client, two_member_circle, auth_headers):
        with patch("app.api.endpoints.recommendations.recommendation_service.get_circle_discovery_artists", new=AsyncMock(return_value=MOCK_ARTISTS)):
            response = await client.get(
                f"/api/v1/recommendations/circle/{two_member_circle.id}/something-new/artists",
                headers=auth_headers,
            )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_discovery_needs_multiple_members(self, client, test_circle, auth_headers):
        response = await client.get(
            f"/api/v1/recommendations/circle/{test_circle.id}/something-new/artists",
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_discovery_requires_membership(self, client, test_circle, second_auth_headers):
        response = await client.get(
            f"/api/v1/recommendations/circle/{test_circle.id}/something-new/artists",
            headers=second_auth_headers,
        )
        assert response.status_code == 403
