import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.circle import CircleUser
from app.models.user import User
from app.services import spotify_service, ticketmaster_service
logger = logging.getLogger(__name__)


def extract_country_code(location: str | None) -> str | None:
    """
    Extracts ISO 3166 country code from user's location string
    Returns None if location is not set or country not recognized
    """
    if not location:
        return None

    # common country name to ISO 3166 code mapping
    country_map = {
        # EUROPE
        "poland": "PL",
        "germany": "DE",
        "united kingdom": "GB", "uk": "GB", "england": "GB", "scotland": "GB", "wales": "GB",
        "france": "FR",
        "netherlands": "NL", "holland": "NL",
        "spain": "ES",
        "italy": "IT",
        "sweden": "SE",
        "norway": "NO",
        "denmark": "DK",
        "belgium": "BE",
        "austria": "AT",
        "switzerland": "CH",
        "czech republic": "CZ", "czechia": "CZ",
        "portugal": "PT",
        "ireland": "IE",
        "finland": "FI",
        "greece": "GR",
        "hungary": "HU",
        "romania": "RO",
        "croatia": "HR",
        "slovakia": "SK",
        "slovenia": "SI",
        "bulgaria": "BG",
        "serbia": "RS",
        "ukraine": "UA",
        "turkey": "TR",
        "iceland": "IS",
        "luxembourg": "LU",
        "lithuania": "LT",
        "latvia": "LV",
        "estonia": "EE",
        # NORTH AMERICA
        "united states": "US", "usa": "US", "america": "US",
        "canada": "CA",
        "mexico": "MX",
    }

    # check from right bc country is usually last part of location string
    parts = [p.strip().lower() for p in location.split(",")]
    for part in reversed(parts):
        if part in country_map:
            return country_map[part]
        if len(part) == 2:  # already a 2-letter code
            return part.upper()

    return None


# async def get_for_you(user: User, db: AsyncSession) -> list[dict]:
#     """
#     FOR YOU - personalized concert recommendations based on user's top artists
#     Gets top artists from Spotify and finds their upcoming concerts on Ticketmaster
#     """
#     top_artists = await spotify_service.get_top_artists(user, db, limit=20)
#     if not top_artists:
#         return []
#
#     artist_names = [a["name"] for a in top_artists]
#     country_code = extract_country_code(user.location)
#
#     return await ticketmaster_service.get_concerts_for_artists(artist_names, country_code)


async def get_discovery_artists(user: User, db: AsyncSession) -> list[dict]:
    """
    Returns a list of artists the user might not know yet
    Sources: artists from top genres + recently played artists
    Excludes top artists (medium_term)
    Filters by popularity (25, 85)
    """
    top_artists = await spotify_service.get_top_artists(user, db, limit=20)
    recently_played = await spotify_service.get_recently_played_artists(user, db)

    # exclude top artists
    known_ids = {a["id"] for a in top_artists}

    # get genres from top artists
    genres = set()
    for artist in top_artists:
        genres.update(artist.get("genres", []))

    # source 1: artists from top genres
    candidate_artists = []
    for genre in list(genres)[:5]:
        results = await spotify_service.search_artists_by_genre(user, db, genre, limit=50)
        for artist in results:
            if (
                artist["id"] not in known_ids
                and 25 < artist["popularity"] < 85
            ):
                candidate_artists.append(artist)

    # source 2: recently played artists (exclude top artists)
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

    unique_artists.sort(key=lambda a: a.get("popularity", 0), reverse=True)
    return unique_artists


# async def get_circle_for_you(circle_id: int, current_user: User, db: AsyncSession) -> list[dict]:
#     """
#     CIRCLE FOR YOU - concert recommendations for circle of friends
#     Score-based algorithm: artists liked by more members get higher score
#     Artists liked by at least half the circle get recommended
#     """
#     members = list(await db.scalars(
#         select(CircleUser).where(CircleUser.circle_id == circle_id)
#     ))
#     if not members:
#         return []
#
#     # score artists by how many members like them
#     artist_scores: dict[str, int] = {}
#     artist_names_map: dict[str, str] = {}  # spotify_id -> name
#
#     for member in members:  # max 4 members
#         member_user = await db.get(User, member.user_id)
#         if not member_user:
#             continue
#
#         top_artists = await spotify_service.get_top_artists(member_user, db, limit=20)
#         for artist in top_artists:
#             sid = artist["id"]
#             artist_scores[sid] = artist_scores.get(sid, 0) + 1
#             artist_names_map[sid] = artist["name"]
#
#     if not artist_scores:
#         return []
#
#     # take artists liked by at least half the circle
#     min_score = max(2, len(members) // 2)
#     top_shared = [
#         artist_names_map[sid]
#         for sid, score in sorted(artist_scores.items(), key=lambda x: -x[1])
#         if score >= min_score
#     ]
#
#     if not top_shared:
#         # fallback - take top 10 scored artists if no shared ones found
#         top_shared = [
#             artist_names_map[sid]
#             for sid, _ in sorted(artist_scores.items(), key=lambda x: -x[1])[:10]
#         ]
#
#     country_code = extract_country_code(current_user.location)
#     return await ticketmaster_service.get_concerts_for_artists(top_shared, country_code)
#
