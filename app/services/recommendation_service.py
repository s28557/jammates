import asyncio
import random
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services import spotify_service
from sqlalchemy import select
from app.models.circle import CircleUser
logger = logging.getLogger(__name__)


def dedupe_artists(artists: list[dict]) -> list[dict]:
    return list({a["id"]: a for a in artists}.values())


# time_range options: short_term (4 weeks), medium_term (6 months), long_term (years; not specified)

async def get_for_you_artists(user: User, db: AsyncSession) -> list[dict]:
    """
    Returns a deduplicated list of artists for the For You feature
    Sources: medium_term top artists + long_term top artists + random 30 followed artists
    Random 30 keeps the list at an ok size
    """
    # refresh once up front so parallel Spotify calls never refresh concurrently
    user = await spotify_service.refresh_token_if_needed(user, db)
    medium_term, long_term, followed = await asyncio.gather(
        spotify_service.get_top_artists(user, db, limit=50, time_range="medium_term"),
        spotify_service.get_top_artists(user, db, limit=50, time_range="long_term"),
        spotify_service.get_followed_artists(user, db),
    )

    # randomly pick 30 followed artists - keeps list manageable
    followed_sample = random.sample(followed, min(30, len(followed)))

    # combine all sources and deduplicate
    all_artists = dedupe_artists(medium_term + long_term + followed_sample)

    # fallback to short_term if user has no medium or long term data
    if not medium_term and not long_term:
        short_term = await spotify_service.get_top_artists(user, db, limit=50, time_range="short_term")
        all_artists = dedupe_artists(all_artists + short_term)

    return all_artists


async def get_known_artist_ids(user: User, db: AsyncSession) -> set[str]:
    """
    Gets IDs of ALL artists the user already knows
    Used only as exclusion filter for Something New
    Includes ALL followed artists to prevent overlap in For You and Something New
    """
    medium_term, long_term, followed = await asyncio.gather(
        spotify_service.get_top_artists(user, db, limit=50, time_range="medium_term"),
        spotify_service.get_top_artists(user, db, limit=50, time_range="long_term"),
        spotify_service.get_followed_artists(user, db),
    )
    return {
        artist["id"]
        for artist in medium_term + long_term + followed
    }


async def get_discovery_artists(user: User, db: AsyncSession) -> list[dict]:
    """
    Returns a list of artists the user might not know yet
    Sources: artists from top genres + recently played artists
    Excludes all known artists : medium_term + long_term + all followed
    Filters by popularity (25, 85)
    """
    # refresh once up front so parallel Spotify calls never refresh concurrently
    user = await spotify_service.refresh_token_if_needed(user, db)
    known_ids, top_artists, recently_played = await asyncio.gather(
        get_known_artist_ids(user, db),
        spotify_service.get_top_artists(user, db, limit=20),  # needed for genres
        spotify_service.get_recently_played_artists(user, db),
    )

    # get genres from top artists
    genres = set()
    for artist in top_artists:
        genres.update(artist.get("genres", []))

    # source artists from top genres, searched in parallel
    candidate_artists = []
    genre_results = await asyncio.gather(*[
        spotify_service.search_artists_by_genre(user, db, genre, limit=50)
        for genre in list(genres)[:5]
    ])
    for results in genre_results:
        for artist in results:
            if (
                artist["id"] not in known_ids
                and 25 < artist["popularity"] < 85
            ):
                candidate_artists.append(artist)

    # source recently played artists (exclude known artists)
    for artist in recently_played:
        if artist["id"] not in known_ids:
            candidate_artists.append(artist)

    unique_artists = dedupe_artists(candidate_artists)

    # recently played artists don't have popularity
    # they're at the bottom of the list as "backup"
    unique_artists.sort(key=lambda a: a.get("popularity", 0), reverse=True)
    return unique_artists


def get_match_type(score: int, member_count: int) -> str:
    """
    Gets match type based on score and circle size
    For 2-member circles there is no partial, only shared or personal
    """
    if score == member_count:
        return "shared"
    if member_count >= 3 and score > member_count / 2:
        return "partial"
    return "personal"


async def get_circle_for_you_artists(circle_id: int, db: AsyncSession) -> list[dict]:
    """
    Returns a list of artists for the Circle For You
    Up to 150 artists, tries to return at least 30 if enough data exists
    Split into groups based on circle size:
    - 2 members: 80% shared, 10% per person (no partial)
    - 3-4 members: 60% shared, 25% partial (majority), 15% personal
    Each artist has match_info showing who likes them
    Personal picks and fallbacks are selected through round-robin
    If a group has too few artists, fills from the next group
    """
    members = list(await db.scalars(
        select(CircleUser).where(CircleUser.circle_id == circle_id)
    ))
    if not members:
        return []

    member_count = len(members)
    min_total = 30
    max_total = 150

    # score artists and track who likes them
    artist_scores: dict[str, int] = {}
    artist_liked_by: dict[str, set[int]] = {}  # spotify_id -> set of user_ids
    artist_data: dict[str, dict] = {}
    personal_artists: dict[int, list[dict]] = {m.user_id: [] for m in members}

    for member in members:
        member_user = await db.get(User, member.user_id)
        if not member_user:
            continue

        top_artists = await spotify_service.get_top_artists(member_user, db, limit=50)
        for artist in top_artists:
            sid = artist["id"]
            artist_scores[sid] = artist_scores.get(sid, 0) + 1
            artist_liked_by.setdefault(sid, set()).add(member.user_id)
            artist_data[sid] = artist

        personal_artists[member.user_id] = top_artists

    # calculate target based on available artists, not fixed max
    available_total = len(artist_scores)
    target_total = max(min_total, min(max_total, available_total))

    if member_count == 2:
        shared_target = int(target_total * 0.80)
        partial_target = 0
        personal_per_member = int(target_total * 0.10)
    else:
        shared_target = int(target_total * 0.60)
        partial_target = int(target_total * 0.25)
        personal_per_member = int(target_total * 0.15) // member_count

    def build_artist_with_match_info(sid: str) -> dict:
        """Builds artist dict with consistent match_info"""
        artist = dict(artist_data[sid])
        liked_by_ids = sorted(artist_liked_by[sid])
        score = len(liked_by_ids)
        artist["match_info"] = {
            "type": get_match_type(score, member_count),
            "liked_by_count": score,
            "liked_by_user_ids": liked_by_ids,
            "liked_by_all": score == member_count,
        }
        return artist

    # split into groups
    shared = []
    partial = []

    for sid, score in sorted(artist_scores.items(), key=lambda x: -x[1]):
        match_type = get_match_type(score, member_count)
        artist = build_artist_with_match_info(sid)
        if match_type == "shared":
            shared.append(artist)
        elif match_type == "partial":
            partial.append(artist)

    # personal picks - unique per member, picked round-robin for fair balance
    shared_partial_ids = {a["id"] for a in shared + partial}
    personal_candidates_by_member = []
    for member in members:
        member_top = personal_artists.get(member.user_id, [])
        unique = [a for a in member_top if a["id"] not in shared_partial_ids]
        personal_candidates_by_member.append(unique)

    personal_picks = []
    personal_pick_ids = set()
    for i in range(personal_per_member):
        for member_candidates in personal_candidates_by_member:
            if i < len(member_candidates):
                sid = member_candidates[i]["id"]
                if sid not in personal_pick_ids:
                    personal_picks.append(build_artist_with_match_info(sid))
                    personal_pick_ids.add(sid)

    # build final list respecting targets
    result = []
    result.extend(shared[:shared_target])

    # if not enough shared, fill with partial
    remaining_shared = shared_target - len(result)
    partial_start = 0
    if remaining_shared > 0:
        result.extend(partial[:remaining_shared])
        partial_start = remaining_shared

    result.extend(partial[partial_start:partial_start + partial_target])
    result.extend(personal_picks[:target_total - len(result)])

    # if still under min, fill with remaining personal artists round-robin
    if len(result) < min_total:
        result_ids = {a["id"] for a in result}
        member_remaining = []
        for member in members:
            member_top = personal_artists.get(member.user_id, [])
            remaining = [a for a in member_top if a["id"] not in result_ids]
            member_remaining.append(remaining)

        i = 0
        while len(result) < min_total:
            added_any = False
            for member_candidates in member_remaining:
                if i < len(member_candidates):
                    sid = member_candidates[i]["id"]
                    if sid not in result_ids:
                        result.append(build_artist_with_match_info(sid))
                        result_ids.add(sid)
                        added_any = True
                    if len(result) >= min_total:
                        break
            i += 1
            if not added_any:
                break

    return dedupe_artists(result)


async def get_circle_discovery_artists(circle_id: int, current_user: User, db: AsyncSession) -> list[dict]:
    """
    Returns discovery artists for a circle, artists none of the members know yet
    Sources: artists from top genres of ALL members combined
    Excludes all artists known by ANY member (medium_term + long_term + followed)
    Filters by popularity (20, 85)
    Sorted by genre_score (how many members share that genre) descending
    """
    members = list(await db.scalars(
        select(CircleUser).where(CircleUser.circle_id == circle_id)
    ))
    if not members:
        return []

    # collect known artists and genres from all members
    all_known_ids: set[str] = set()
    genre_scores: dict[str, int] = {}  # genre -> how many members have it

    for member in members:
        member_user = await db.get(User, member.user_id)
        if not member_user:
            continue

        # get known artists for this member, refreshing the token once first
        member_user = await spotify_service.refresh_token_if_needed(member_user, db)
        medium_term, long_term, followed = await asyncio.gather(
            spotify_service.get_top_artists(member_user, db, limit=50, time_range="medium_term"),
            spotify_service.get_top_artists(member_user, db, limit=50, time_range="long_term"),
            spotify_service.get_followed_artists(member_user, db),
        )

        for artist in medium_term + long_term + followed:
            all_known_ids.add(artist["id"])

        # collect genres from medium_term top artists
        for artist in medium_term:
            for genre in artist.get("genres", []):
                genre_scores[genre] = genre_scores.get(genre, 0) + 1

    # take top 10 genres by score (most shared across members)
    top_genres = sorted(genre_scores.items(), key=lambda x: -x[1])[:10]

    # search artists by top genres
    candidate_artists = []
    seen_ids = set()

    # use current user's token for search, all genres in parallel
    current_user = await spotify_service.refresh_token_if_needed(current_user, db)
    genre_results = await asyncio.gather(*[
        spotify_service.search_artists_by_genre(current_user, db, genre, limit=50)
        for genre, _ in top_genres
    ])
    for results in genre_results:
        for artist in results:
            sid = artist["id"]
            if (
                sid not in all_known_ids
                and sid not in seen_ids
                and 20 < artist.get("popularity", 0) < 85
            ):
                # find which genres from top_genres this artist matches
                artist_genres = set(artist.get("genres", []))
                matched_genres = [g for g, _ in top_genres if g in artist_genres]

                artist["discovery_info"] = {
                    "matched_genres": matched_genres,
                    "genre_score": sum(genre_scores.get(g, 0) for g in matched_genres),
                    "source": "circle_discovery",
                }
                candidate_artists.append(artist)
                seen_ids.add(sid)

    # sort by genre_score descending - artists matching more popular genres first
    candidate_artists.sort(
        key=lambda a: a["discovery_info"]["genre_score"],
        reverse=True
    )

    return candidate_artists
