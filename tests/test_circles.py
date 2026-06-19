import io
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.circle import Circle, CircleUser
from app.models.user import User


# Circle creation tests
class TestCreateCircle:

    async def test_success(self, client, auth_headers):
        response = await client.post("/api/v1/circles?name=My+Band", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Band"
        assert "invite_code" in data
        assert "id" in data

    async def test_requires_auth(self, client):
        response = await client.post("/api/v1/circles?name=NeedAuth")
        assert response.status_code == 401

    async def test_enforces_per_user_limit(self, client, db, test_user, auth_headers):
        # fill all circle slots for the user
        for i in range(8):
            circle = Circle(name=f"Circle {i}", invite_code=f"LIMIT{i:04}", created_by=test_user.id)
            db.add(circle)
            await db.flush()
            db.add(CircleUser(circle_id=circle.id, user_id=test_user.id, role="creator"))
        await db.commit()

        response = await client.post("/api/v1/circles?name=OneMore", headers=auth_headers)
        assert response.status_code == 400


# Circle join tests
class TestJoinCircle:

    async def test_with_valid_code(self, client, test_circle, second_auth_headers):
        response = await client.post(
            f"/api/v1/circles/join?invite_code={test_circle.invite_code}",
            headers=second_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["circle"] == test_circle.name

    async def test_with_invalid_code(self, client, second_auth_headers):
        response = await client.post(
            "/api/v1/circles/join?invite_code=DOESNOTEXIST",
            headers=second_auth_headers,
        )
        assert response.status_code == 404

    async def test_when_already_member(self, client, test_circle, auth_headers):
        response = await client.post(
            f"/api/v1/circles/join?invite_code={test_circle.invite_code}",
            headers=auth_headers,
        )
        assert response.status_code == 400

    async def test_full_circle(self, client, db, test_circle):
        # add enough extra members to hit circle capacity
        for i in range(3):
            u = User(
                spotify_id=f"extra_user_{i}",
                email=f"extra{i}@example.com",
                access_token="tok",
                refresh_token="ref",
                token_expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            )
            db.add(u)
            await db.flush()
            db.add(CircleUser(circle_id=test_circle.id, user_id=u.id, role="member"))
        await db.commit()

        overflow = User(
            spotify_id="overflow_user_99",
            email="overflow@example.com",
            access_token="tok",
            refresh_token="ref",
            token_expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )
        db.add(overflow)
        await db.commit()
        await db.refresh(overflow)

        token = create_access_token(overflow.id)
        response = await client.post(
            f"/api/v1/circles/join?invite_code={test_circle.invite_code}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


# My circles listing tests
class TestMyCircles:

    async def test_empty(self, client, auth_headers):
        response = await client.get("/api/v1/circles/my", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_joined_circles(self, client, test_circle, auth_headers):
        response = await client.get("/api/v1/circles/my", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == test_circle.name
        assert data[0]["invite_code"] == test_circle.invite_code


# Circle image URL tests
class TestCircleImageUrl:

    async def test_member_can_update(self, client, test_circle, auth_headers):
        response = await client.patch(
            f"/api/v1/circles/{test_circle.id}/image?image_url=https://example.com/new.jpg",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["image_url"] == "https://example.com/new.jpg"

    async def test_non_member_blocked(self, client, test_circle, second_auth_headers):
        response = await client.patch(
            f"/api/v1/circles/{test_circle.id}/image?image_url=https://example.com/new.jpg",
            headers=second_auth_headers,
        )
        assert response.status_code == 403

    async def test_clear_image(self, client, test_circle, auth_headers):
        response = await client.patch(
            f"/api/v1/circles/{test_circle.id}/image",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["image_url"] is None


# Circle name update tests
class TestCircleName:

    async def test_admin_can_rename(self, client, test_circle, auth_headers):
        response = await client.patch(
            f"/api/v1/circles/{test_circle.id}/name?name=NewName",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "NewName"

    async def test_non_admin_blocked(self, client, db, test_circle, second_user, second_auth_headers):
        # make the second user a non-admin member
        db.add(CircleUser(circle_id=test_circle.id, user_id=second_user.id, role="member"))
        await db.commit()

        response = await client.patch(
            f"/api/v1/circles/{test_circle.id}/name?name=NewName",
            headers=second_auth_headers,
        )
        assert response.status_code == 403

    async def test_empty_name_rejected(self, client, test_circle, auth_headers):
        response = await client.patch(
            f"/api/v1/circles/{test_circle.id}/name?name=++++",
            headers=auth_headers,
        )
        assert response.status_code == 400


# Circle image upload tests
class TestUploadCircleImage:

    async def test_valid_jpeg(self, client, test_circle, auth_headers):
        image_bytes = b"\xff\xd8\xff" + b"\x00" * 100  # minimal fake JPEG header
        # avoid writing uploaded files during tests
        with patch.object(Path, "write_bytes"), patch.object(Path, "mkdir"):
            response = await client.post(
                f"/api/v1/circles/{test_circle.id}/image/upload",
                headers=auth_headers,
                files={"image": ("photo.jpg", io.BytesIO(image_bytes), "image/jpeg")},
            )
        assert response.status_code == 200
        assert "image_url" in response.json()

    async def test_unsupported_type_rejected(self, client, test_circle, auth_headers):
        response = await client.post(
            f"/api/v1/circles/{test_circle.id}/image/upload",
            headers=auth_headers,
            files={"image": ("file.txt", io.BytesIO(b"text content"), "text/plain")},
        )
        assert response.status_code == 400

    async def test_non_member_blocked(self, client, test_circle, second_auth_headers):
        response = await client.post(
            f"/api/v1/circles/{test_circle.id}/image/upload",
            headers=second_auth_headers,
            files={"image": ("photo.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
        assert response.status_code == 403


# Circle leave tests
class TestLeaveCircle:

    async def test_last_member_deletes_circle(self, client, db, test_circle, auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{test_circle.id}/leave",
            headers=auth_headers,
        )
        assert response.status_code == 204
        assert await db.get(Circle, test_circle.id) is None

    async def test_member_leaves_circle_survives(self, client, db, two_member_circle, second_auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{two_member_circle.id}/leave",
            headers=second_auth_headers,
        )
        assert response.status_code == 204
        assert await db.get(Circle, two_member_circle.id) is not None

    async def test_creator_leaving_transfers_admin(self, client, db, two_member_circle, second_user, auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{two_member_circle.id}/leave",
            headers=auth_headers,
        )
        assert response.status_code == 204

        new_creator = await db.scalar(
            select(CircleUser).where(
                CircleUser.circle_id == two_member_circle.id,
                CircleUser.user_id == second_user.id,
            )
        )
        assert new_creator is not None
        assert new_creator.role == "creator"


# Circle member removal tests
class TestRemoveMember:

    async def test_admin_can_remove(self, client, db, two_member_circle, second_user, auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{two_member_circle.id}/members/{second_user.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        membership = await db.scalar(
            select(CircleUser).where(
                CircleUser.circle_id == two_member_circle.id,
                CircleUser.user_id == second_user.id,
            )
        )
        assert membership is None

    async def test_non_admin_blocked(self, client, two_member_circle, test_user, second_auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{two_member_circle.id}/members/{test_user.id}",
            headers=second_auth_headers,
        )
        assert response.status_code == 403

    async def test_cannot_remove_self(self, client, test_circle, test_user, auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{test_circle.id}/members/{test_user.id}",
            headers=auth_headers,
        )
        assert response.status_code == 400

    async def test_nonexistent_member(self, client, test_circle, auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{test_circle.id}/members/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404


# Circle delete tests
class TestDeleteCircle:

    async def test_admin_can_delete(self, client, db, test_circle, auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{test_circle.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
        assert await db.get(Circle, test_circle.id) is None

    async def test_non_admin_blocked(self, client, two_member_circle, second_auth_headers):
        response = await client.delete(
            f"/api/v1/circles/{two_member_circle.id}",
            headers=second_auth_headers,
        )
        assert response.status_code == 403


# Circle members listing tests
class TestCircleMembers:

    async def test_returns_all_members(self, client, two_member_circle, auth_headers):
        response = await client.get(
            f"/api/v1/circles/{two_member_circle.id}/members",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        roles = {m["role"] for m in data}
        assert "creator" in roles
        assert "member" in roles

    async def test_marks_current_user(self, client, two_member_circle, auth_headers):
        response = await client.get(
            f"/api/v1/circles/{two_member_circle.id}/members",
            headers=auth_headers,
        )
        assert response.status_code == 200
        current = next(m for m in response.json() if m["is_current_user"])
        assert current["role"] == "creator"

    async def test_non_member_blocked(self, client, test_circle, second_auth_headers):
        response = await client.get(
            f"/api/v1/circles/{test_circle.id}/members",
            headers=second_auth_headers,
        )
        assert response.status_code == 403
