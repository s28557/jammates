import asyncio
import random
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services import spotify_service
from sqlalchemy import select
from app.models.circle import CircleUser
logger = logging.getLogger(__name__)


# continent to Ticketmaster country codes mapping
CONTINENT_COUNTRY_CODES = {
    "Europe": ["PL", "DE", "GB", "FR", "NL", "ES", "IT", "SE", "NO", "DK",
               "BE", "AT", "CH", "CZ", "PT", "IE", "FI", "GR", "HU", "RO",
               "HR", "SK", "SI", "BG", "RS", "UA", "TR", "IS", "LU", "LT", "LV", "EE"],
    "North America": ["US", "CA", "MX"],
}


def get_country_codes_for_continent(continent: str | None) -> list[str] | None:
    """
    Gets list of Ticketmaster country codes for a given continent
    Returns None if continent is not set - means no country filtering
    """
    if not continent:
        return None
    return CONTINENT_COUNTRY_CODES.get(continent)


# time_range options: short_term (4 weeks), medium_term (6 months), long_term (years)

async def get_for_you_artists(user: User, db: AsyncSession) -> list[dict]:
    """
    Returns a deduplicated list of artists for the For You feature
    Sources: medium_term top artists + long_term top artists + random 30 followed artists
    Random 30 keeps the list at an ok size
    """
    medium_term, long_term, followed = await asyncio.gather(
        spotify_service.get_top_artists(user, db, limit=50, time_range="medium_term"),
        spotify_service.get_top_artists(user, db, limit=50, time_range="long_term"),
        spotify_service.get_followed_artists(user, db),
    )

    # randomly pick 30 followed artists - keeps list manageable
    followed_sample = random.sample(followed, min(30, len(followed)))

    # combine all sources and deduplicate
    seen_ids = set()
    all_artists = []
    for artist in medium_term + long_term + followed_sample:
        if artist["id"] not in seen_ids:
            seen_ids.add(artist["id"])
            all_artists.append(artist)

    # fallback to short_term if user has no medium or long term data
    if not medium_term and not long_term:
        short_term = await spotify_service.get_top_artists(user, db, limit=50, time_range="short_term")
        for artist in short_term:
            if artist["id"] not in seen_ids:
                seen_ids.add(artist["id"])
                all_artists.append(artist)

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
    known_ids, top_artists, recently_played = await asyncio.gather(
        get_known_artist_ids(user, db),
        spotify_service.get_top_artists(user, db, limit=20),  # needed for genres
        spotify_service.get_recently_played_artists(user, db),
    )

    # get genres from top artists
    genres = set()
    for artist in top_artists:
        genres.update(artist.get("genres", []))

    # source artists from top genres
    candidate_artists = []
    for genre in list(genres)[:5]:
        results = await spotify_service.search_artists_by_genre(user, db, genre, limit=50)
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

    # remove duplicates
    seen_ids = set()
    unique_artists = []
    for artist in candidate_artists:
        if artist["id"] not in seen_ids:
            seen_ids.add(artist["id"])
            unique_artists.append(artist)

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

    # personal picks - unique per member
    shared_partial_ids = {a["id"] for a in shared + partial}
    personal_picks = []
    for member in members:
        member_top = personal_artists.get(member.user_id, [])
        unique = [a for a in member_top if a["id"] not in shared_partial_ids]
        for artist in unique[:personal_per_member]:
            personal_picks.append(build_artist_with_match_info(artist["id"]))

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

    # if still under min, fill with remaining artists by score
    if len(result) < min_total:
        result_ids = {a["id"] for a in result}
        for sid, _ in sorted(artist_scores.items(), key=lambda x: -x[1]):
            if len(result) >= min_total:
                break
            if sid not in result_ids:
                result.append(build_artist_with_match_info(sid))
                result_ids.add(sid)

    # deduplicate just in case
    seen_ids = set()
    unique_result = []
    for artist in result:
        if artist["id"] not in seen_ids:
            seen_ids.add(artist["id"])
            unique_result.append(artist)

    return unique_result