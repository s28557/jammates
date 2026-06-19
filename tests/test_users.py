from app.core.security import create_access_token


class TestGetMe:

    async def test_returns_profile(self, client, test_user, auth_headers):
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["display_name"] == test_user.display_name
        assert data["avatar_url"] == test_user.avatar_url

    async def test_without_token(self, client):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_with_invalid_token(self, client):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    async def test_with_nonexistent_user_token(self, client):
        token = create_access_token(user_id=99999)
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
