from unittest.mock import AsyncMock, patch
from app.services.circle_taste_service import (
    get_artist_pool,
    get_pair_match,
    get_shared_genres,
    get_shared_items,
    get_unique_artists,
)


def artist(artist_id, genres=()):
    return {"id": artist_id, "name": artist_id.title(), "genres": list(genres), "image_url": None}


def track(track_id, artist_ids=(), image_url=None):
    return {
        "id": track_id,
        "name": track_id.title(),
        "artist": "Someone",
        "artists": [{"id": artist_id, "name": artist_id.title()} for artist_id in artist_ids],
        "image_url": image_url,
    }


def member(member_id, artists, tracks=()):
    return {"id": member_id, "artists": artists, "tracks": list(tracks), "pool": get_artist_pool(artists, list(tracks))}


# Circle taste endpoint tests
class TestCircleTasteEndpoint:

    async def test_returns_blend(self, client, two_member_circle, auth_headers, test_user, second_user):
        tastes = {
            test_user.id: {"artists": [artist("beatles", ["rock"]), artist("kanye", ["rap"])], "tracks": [track("let-it-be")]},
            second_user.id: {"artists": [artist("beatles", ["rock"]), artist("lana", ["pop"])], "tracks": [track("let-it-be")]},
        }

        async def fake_member_taste(user, db, time_range):
            return tastes[user.id]

        with patch("app.services.circle_taste_service.get_member_taste", new=fake_member_taste):
            response = await client.get(
                f"/api/v1/recommendations/circle/{two_member_circle.id}/taste?time_range=long_term",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["pairs"]) == 1
        assert data["match"] == data["pairs"][0]["match"]
        assert [item["id"] for item in data["shared_artists"]] == ["beatles"]
        assert [item["id"] for item in data["shared_tracks"]] == ["let-it-be"]
        assert data["shared_genres"][0]["name"] == "rock"
        current = next(item for item in data["members"] if item["is_current_user"])
        assert [item["id"] for item in current["unique_artists"]] == ["kanye"]

    async def test_members_without_data_sit_out_the_match(self, client, two_member_circle, auth_headers, test_user, second_user):
        tastes = {
            test_user.id: {"artists": [artist("beatles", ["rock"])], "tracks": []},
            second_user.id: {"artists": [], "tracks": []},
        }

        async def fake_member_taste(user, db, time_range):
            return tastes[user.id]

        with patch("app.services.circle_taste_service.get_member_taste", new=fake_member_taste):
            response = await client.get(
                f"/api/v1/recommendations/circle/{two_member_circle.id}/taste",
                headers=auth_headers,
            )

        data = response.json()
        assert data["pairs"] == []
        assert data["match"] is None
        assert [item["has_data"] for item in data["members"]] == [True, False]

    async def test_passes_time_range(self, client, two_member_circle, auth_headers):
        mock = AsyncMock(return_value={"artists": [], "tracks": []})
        with patch("app.services.circle_taste_service.get_member_taste", new=mock):
            await client.get(
                f"/api/v1/recommendations/circle/{two_member_circle.id}/taste?time_range=short_term",
                headers=auth_headers,
            )
        assert all(call.args[2] == "short_term" for call in mock.call_args_list)

    async def test_needs_multiple_members(self, client, test_circle, auth_headers):
        response = await client.get(f"/api/v1/recommendations/circle/{test_circle.id}/taste", headers=auth_headers)
        assert response.status_code == 409

    async def test_requires_membership(self, client, test_circle, second_auth_headers):
        response = await client.get(f"/api/v1/recommendations/circle/{test_circle.id}/taste", headers=second_auth_headers)
        assert response.status_code == 403


# Circle taste helpers tests
class TestCircleTasteHelpers:

    def test_identical_taste_scores_higher_than_different(self):
        first = member(1, [artist("a", ["rock"]), artist("b", ["rock"])])
        same = member(2, [artist("a", ["rock"]), artist("b", ["rock"])])
        other = member(3, [artist("c", ["jazz"]), artist("d", ["jazz"])])
        assert get_pair_match(first, same) > get_pair_match(first, other)
        assert get_pair_match(first, other) == 0
        assert 0 < get_pair_match(first, same) <= 100

    def test_match_uses_artists_only_without_genres(self):
        first = member(1, [artist("a"), artist("b")])
        second = member(2, [artist("a"), artist("c")])
        assert get_pair_match(first, second) > 0

    def test_match_is_zero_for_empty_lists(self):
        assert get_pair_match(member(1, []), member(2, [artist("a")])) == 0

    def test_shared_items_need_two_members_and_rank_by_count(self):
        members = [
            member(1, [artist("solo"), artist("pair"), artist("all")]),
            member(2, [artist("all"), artist("pair")]),
            member(3, [artist("all")]),
        ]
        shared = get_shared_items(members, "artists", limit=10)
        assert [item["id"] for item in shared] == ["all", "pair"]
        assert shared[0]["liked_by"] == [1, 2, 3]
        assert "rank_sum" not in shared[0]

    def test_shared_genres_need_two_members(self):
        members = [
            member(1, [artist("a", ["rock", "jazz"])]),
            member(2, [artist("b", ["rock"])]),
        ]
        assert get_shared_genres(members, limit=10) == [{"name": "rock", "liked_by": [1, 2]}]

    def test_unique_artists_skip_anyone_elses(self):
        members = [
            member(1, [artist("shared"), artist("mine")]),
            member(2, [artist("shared"), artist("theirs")]),
        ]
        unique = get_unique_artists(members, limit=4)
        assert [item["id"] for item in unique[1]] == ["mine"]
        assert [item["id"] for item in unique[2]] == ["theirs"]

    def test_pool_adds_track_artists_after_top_artists(self):
        pool = get_artist_pool(
            [artist("beatles", ["rock"])],
            [track("hey-jude", ["beatles"]), track("honesty", ["billy-joel"], image_url="cover.jpg")],
        )
        assert [item["id"] for item in pool] == ["beatles", "billy-joel"]
        assert pool[1]["image_url"] == "cover.jpg"
        assert pool[1]["from_tracks"] is True

    def test_shared_artists_count_track_artists(self):
        members = [
            member(1, [artist("billy-joel")]),
            member(2, [artist("raye")], [track("honesty", ["billy-joel"])]),
        ]
        shared = get_shared_items(members, "pool", limit=10)
        assert [item["id"] for item in shared] == ["billy-joel"]
        assert "from_tracks" not in shared[0]

    def test_shared_artist_prefers_top_artist_entry(self):
        members = [
            member(1, [], [track("honesty", ["billy-joel"], image_url="cover.jpg")]),
            member(2, [{**artist("billy-joel", ["soft rock"]), "image_url": "photo.jpg"}]),
        ]
        shared = get_shared_items(members, "pool", limit=10)
        assert shared[0]["image_url"] == "photo.jpg"
        assert shared[0]["genres"] == ["soft rock"]
        assert shared[0]["liked_by"] == [1, 2]

    def test_unique_artists_skip_others_track_artists(self):
        members = [
            member(1, [artist("billy-joel"), artist("kanye")]),
            member(2, [artist("raye")], [track("honesty", ["billy-joel"])]),
        ]
        unique = get_unique_artists(members, limit=4)
        assert [item["id"] for item in unique[1]] == ["kanye"]
