import asyncio
import math
from itertools import combinations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.circle import CircleUser
from app.models.user import User
from app.services import spotify_service

SHARED_ARTISTS_LIMIT = 20
SHARED_GENRES_LIMIT = 8
SHARED_TRACKS_LIMIT = 10
UNIQUE_ARTISTS_PER_MEMBER = 4
# raw overlap of two top-50 lists is small even for very similar taste (12 shared artists is a lot),
# so the raw value is spread with 1 - e^(-k * raw): 0.06 -> ~21%, 0.28 -> ~68%
MATCH_CURVE = 4


def get_genre_weights(artists: list[dict]) -> dict[str, float]:
    """
    Genre weights from a ranked artist list, higher ranked artists weigh more
    """
    weights: dict[str, float] = {}
    for rank, artist in enumerate(artists):
        for genre in artist.get("genres", []):
            weights[genre] = weights.get(genre, 0) + len(artists) - rank
    return weights


def cosine_similarity(first: dict[str, float], second: dict[str, float]) -> float:
    dot = sum(value * second.get(key, 0) for key, value in first.items())
    first_norm = math.sqrt(sum(value * value for value in first.values()))
    second_norm = math.sqrt(sum(value * value for value in second.values()))
    if not first_norm or not second_norm:
        return 0.0
    return dot / (first_norm * second_norm)


def get_artist_pool(artists: list[dict], tracks: list[dict]) -> list[dict]:
    """
    Top artists followed by the artists of top tracks that are not already in the list
    Spotify's top artists list is short for people who listen less, top tracks fill the gaps
    Track artists have no photo or genres, so they borrow the album cover until a member has them as a top artist
    """
    pool = list(artists)
    seen = {artist["id"] for artist in artists}
    for track in tracks:
        for track_artist in track.get("artists", []):
            if track_artist["id"] in seen:
                continue
            seen.add(track_artist["id"])
            pool.append({
                "id": track_artist["id"],
                "name": track_artist["name"],
                "genres": [],
                "image_url": track.get("image_url"),
                "from_tracks": True,
            })
    return pool


def get_pair_match(first: dict, second: dict) -> int:
    """
    Taste match of two members as a 0-100 score
    Half artist overlap (shared artists from top artists and top tracks vs the shorter pool),
    half genre similarity of top artists, then spread with MATCH_CURVE
    Genres are often missing on Spotify, so without them the score uses artists only
    """
    first_ids = {artist["id"] for artist in first["pool"]}
    second_ids = {artist["id"] for artist in second["pool"]}
    shorter = min(len(first_ids), len(second_ids))
    if not shorter:
        return 0

    artist_overlap = len(first_ids & second_ids) / shorter
    first_genres = get_genre_weights(first["artists"])
    second_genres = get_genre_weights(second["artists"])

    if not first_genres or not second_genres:
        raw = artist_overlap
    else:
        raw = artist_overlap * 0.5 + cosine_similarity(first_genres, second_genres) * 0.5

    return round((1 - math.exp(-MATCH_CURVE * raw)) * 100)


def get_shared_items(members: list[dict], key: str, limit: int) -> list[dict]:
    """
    Artists or tracks that at least two members have in their top lists
    Sorted by how many members like them, then by their combined rank
    """
    items: dict[str, dict] = {}
    for member in members:
        for rank, item in enumerate(member[key]):
            entry = items.setdefault(item["id"], {**item, "liked_by": [], "rank_sum": 0})
            # prefer a real top artist entry (photo, genres) over one taken from a track
            if entry.get("from_tracks") and not item.get("from_tracks"):
                entry.update({**item, "liked_by": entry["liked_by"], "rank_sum": entry["rank_sum"]})
            entry["liked_by"].append(member["id"])
            entry["rank_sum"] += rank

    shared = [item for item in items.values() if len(item["liked_by"]) >= 2]
    shared.sort(key=lambda item: (-len(item["liked_by"]), item["rank_sum"]))
    return [
        {k: v for k, v in item.items() if k not in ("rank_sum", "from_tracks")}
        for item in shared[:limit]
    ]


def get_shared_genres(members: list[dict], limit: int) -> list[dict]:
    """
    Genres that at least two members share, sorted by member count then combined weight
    """
    genres: dict[str, dict] = {}
    for member in members:
        for genre, weight in get_genre_weights(member["artists"]).items():
            entry = genres.setdefault(genre, {"name": genre, "liked_by": [], "weight": 0})
            entry["liked_by"].append(member["id"])
            entry["weight"] += weight

    shared = [genre for genre in genres.values() if len(genre["liked_by"]) >= 2]
    shared.sort(key=lambda genre: (-len(genre["liked_by"]), -genre["weight"]))
    return [{"name": genre["name"], "liked_by": genre["liked_by"]} for genre in shared[:limit]]


def get_unique_artists(members: list[dict], limit: int) -> dict[int, list[dict]]:
    """
    Each member's highest ranked top artists that nobody else has in their top artists or top tracks
    """
    unique: dict[int, list[dict]] = {}
    for member in members:
        others = {
            artist["id"]
            for other in members if other["id"] != member["id"]
            for artist in other["pool"]
        }
        unique[member["id"]] = [artist for artist in member["artists"] if artist["id"] not in others][:limit]
    return unique


async def get_member_taste(user: User, db: AsyncSession, time_range: str) -> dict:
    # refresh once up front so the parallel calls below never refresh concurrently
    user = await spotify_service.refresh_token_if_needed(user, db)
    artists, tracks = await asyncio.gather(
        spotify_service.get_top_artists(user, db, limit=50, time_range=time_range),
        spotify_service.get_top_tracks(user, db, limit=50, time_range=time_range),
    )
    return {"artists": artists, "tracks": tracks}


async def get_circle_taste(circle_id: int, current_user: User, db: AsyncSession, time_range: str = "medium_term") -> dict:
    """
    Blend of a circle's taste: overall and pairwise match, what members share and what each one brings
    """
    rows = await db.execute(
        select(User)
        .join(CircleUser, CircleUser.user_id == User.id)
        .where(CircleUser.circle_id == circle_id)
        .order_by(CircleUser.joined_at.asc())
    )
    users = list(rows.scalars())

    # members load one by one, each refresh writes to the shared db session
    members = []
    for user in users:
        taste = await get_member_taste(user, db, time_range)
        members.append({
            "id": user.id,
            "display_name": user.display_name or user.email or f"User {user.id}",
            "avatar_url": user.avatar_url,
            "is_current_user": user.id == current_user.id,
            "pool": get_artist_pool(taste["artists"], taste["tracks"]),
            **taste,
        })

    # members without listening in this period would score 0 against everyone, so they sit out the match
    rated = [member for member in members if member["pool"]]
    pairs = [
        {"members": [first["id"], second["id"]], "match": get_pair_match(first, second)}
        for first, second in combinations(rated, 2)
    ]
    overall = round(sum(pair["match"] for pair in pairs) / len(pairs)) if pairs else None
    unique = get_unique_artists(members, UNIQUE_ARTISTS_PER_MEMBER)

    return {
        "match": overall,
        "pairs": pairs,
        "members": [
            {
                "id": member["id"],
                "display_name": member["display_name"],
                "avatar_url": member["avatar_url"],
                "is_current_user": member["is_current_user"],
                "has_data": bool(member["pool"]),
                "unique_artists": unique[member["id"]],
            }
            for member in members
        ],
        "shared_artists": get_shared_items(members, "pool", SHARED_ARTISTS_LIMIT),
        "shared_tracks": get_shared_items(members, "tracks", SHARED_TRACKS_LIMIT),
        "shared_genres": get_shared_genres(members, SHARED_GENRES_LIMIT),
    }
