import asyncio
import logging
import re
import unicodedata
import httpx
from datetime import datetime, timezone
from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.services.country_bounds import COUNTRY_BOUNDS
logger = logging.getLogger(__name__)
TICKETMASTER_BASE = "https://app.ticketmaster.com/discovery/v2"
TICKETMASTER_CACHE_TTL_SECONDS = 60 * 60 * 12
TICKETMASTER_CACHE_VERSION = "v3"
# searches are worldwide, so a small page would keep only one region's nearest dates
TICKETMASTER_EVENTS_PER_ARTIST = 50

# one shared client so parallel artist searches reuse connections
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


def parse_coordinate(value: str | float | int | None) -> float | None:
    """
    Converts Ticketmaster venue coordinates to floats when available
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_ticketmaster_cache_key(artist_name: str, country_code: str | None = None) -> str:
    """
    Creates a reusable cache key for Ticketmaster artist concert searches
    """
    artist = artist_name.strip().lower()
    country = country_code.strip().upper() if country_code else "ALL"
    return f"ticketmaster:{TICKETMASTER_CACHE_VERSION}:events:{country}:{artist}"


def get_ticketmaster_start_datetime() -> str:
    """
    Gets current UTC time in Ticketmaster API format
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_event_datetime(value: str | None) -> datetime | None:
    """
    Parses event datetime when Ticketmaster provides exact start time
    """
    if not value or "T" not in value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_event_date(value: str | None):
    """
    Parses event date from local_date or date fallback
    """
    if not value:
        return None

    try:
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return None


def is_upcoming_event(event: dict, now: datetime | None = None) -> bool:
    """
    Checks if event is still upcoming
    """
    now = now or datetime.now(timezone.utc)

    exact_start = parse_event_datetime(event.get("date"))
    if exact_start is not None:
        return exact_start >= now

    event_date = parse_event_date(event.get("local_date") or event.get("date"))
    if event_date is None:
        return False

    return event_date >= now.date()


def filter_upcoming_events(events: list[dict]) -> list[dict]:
    """
    Removes past events from Ticketmaster results
    """
    now = datetime.now(timezone.utc)
    return [event for event in events if is_upcoming_event(event, now)]


def is_inside_country(lat: float, lng: float, country: str | None) -> bool:
    min_lat, max_lat, min_lng, max_lng = COUNTRY_BOUNDS[country]
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def check_event_coordinates(event: dict) -> dict:
    """
    Some venues have broken coordinates (e.g. a dropped minus sign puts
    Corona, CA in China). If the point is outside the event's country, try
    the usual mistakes (flipped signs, swapped lat/lng) and otherwise drop
    the coordinates so the concert stays off the map instead of misplaced
    """
    lat, lng, country = event.get("lat"), event.get("lng"), event.get("country")
    if lat is None or lng is None or country not in COUNTRY_BOUNDS:
        return event
    if is_inside_country(lat, lng, country):
        return event

    for fixed_lat, fixed_lng in ((lat, -lng), (-lat, lng), (-lat, -lng), (lng, lat)):
        if is_inside_country(fixed_lat, fixed_lng, country):
            return {**event, "lat": fixed_lat, "lng": fixed_lng}

    return {**event, "lat": None, "lng": None}


def normalize_match_text(value: str | None) -> str:
    """
    Lowercases, drops accents and punctuation so names compare as plain words
    """
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def is_event_for_artist(event: dict, artist_name: str) -> bool:
    """
    Keyword search also returns other acts that share a word with the artist
    (e.g. "Police Dog Hogan" for "The Police"), so keep only events whose title
    or performers contain the full artist name. Tribute and cover shows that
    name the artist stay in.
    """
    name = normalize_match_text(artist_name)
    if not name:
        return False

    texts = [event.get("name"), *(event.get("performers") or [])]
    return any(f" {name} " in f" {normalize_match_text(text)} " for text in texts)


def filter_artist_events(events: list[dict], artist_name: str) -> list[dict]:
    return [check_event_coordinates(event) for event in events if is_event_for_artist(event, artist_name)]


def map_ticketmaster_event(event: dict, artist_name: str) -> dict:
    """
    Maps raw Ticketmaster event data to the fields the app needs
    """
    venue = {}
    venues = event.get("_embedded", {}).get("venues", [])
    if venues:
        venue = venues[0]

    attractions = event.get("_embedded", {}).get("attractions", [])
    images = event.get("images", [])
    image_url = images[0].get("url") if images else None

    start = event.get("dates", {}).get("start", {})
    city = venue.get("city", {})
    country = venue.get("country", {})
    location = venue.get("location", {})
    lat = parse_coordinate(location.get("latitude"))
    lng = parse_coordinate(location.get("longitude"))

    # Ticketmaster sometimes sends 0,0 for venues without a known location
    if lat == 0 and lng == 0:
        lat = lng = None

    return {
        "id": event.get("id"),
        "name": event.get("name"),
        "url": event.get("url"),
        "artist": artist_name,
        "date": start.get("dateTime") or start.get("localDate"),
        "local_date": start.get("localDate"),
        "local_time": start.get("localTime"),
        "venue": venue.get("name"),
        "city": city.get("name"),
        "country": country.get("countryCode") or country.get("name"),
        "lat": lat,
        "lng": lng,
        "image_url": image_url,
        "performers": [attraction.get("name") for attraction in attractions if attraction.get("name")],
    }


async def get_artist_events(artist_name: str, country_code: str | None = None) -> list[dict]:
    """
    Gets upcoming music events for a given artist from Ticketmaster
    Optionally filters by country code - ISO 3166
    Returns empty list if artist not found or no upcoming events
    """
    cache_key = get_ticketmaster_cache_key(artist_name, country_code)
    cached_events = await cache_get(cache_key)
    if cached_events is not None:
        return filter_artist_events(filter_upcoming_events(cached_events), artist_name)

    params = {
        "apikey": settings.TICKETMASTER_API_KEY,
        "keyword": artist_name,
        "classificationName": "music",  # only music events
        "startDateTime": get_ticketmaster_start_datetime(),
        "sort": "date,asc",             # nearest concerts first
        "size": TICKETMASTER_EVENTS_PER_ARTIST,
    }

    if country_code:
        params["countryCode"] = country_code

    try:
        response = await get_http_client().get(
            f"{TICKETMASTER_BASE}/events.json",
            params=params,
        )

        if response.status_code == 429:
            logger.error("Ticketmaster rate limit exceeded")
            return []
        if response.status_code != 200:
            logger.error(f"Ticketmaster error for {artist_name}: status {response.status_code}")
            return []

        data = response.json()
        # events are nested under _embedded.events
        raw_events = data.get("_embedded", {}).get("events", [])
        events = filter_upcoming_events([
            map_ticketmaster_event(event, artist_name)
            for event in raw_events
        ])
        # cache everything Ticketmaster returned, so the matching rule can change without refetching
        await cache_set(cache_key, events, ttl_seconds=TICKETMASTER_CACHE_TTL_SECONDS)
        return filter_artist_events(events, artist_name)

    except httpx.TimeoutException:
        logger.error(f"Ticketmaster timeout for artist: {artist_name}")
        return []
    except httpx.RequestError as e:
        # network error, DNS failure, connection refused etc
        logger.error(f"Ticketmaster request error for {artist_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Ticketmaster unexpected error for {artist_name}: {e}")
        return []


async def get_concerts_for_artists(artist_names: list[str], country_code: str | None = None) -> list[dict]:
    """
    Gets upcoming concerts for a list of artists at the same time
    Filters by country if user has location set
    Deduplicates events by Ticketmaster event ID
    """
    if not artist_names:
        return []

    # get all artists at the same time
    tasks = [get_artist_events(name, country_code) for name in artist_names]
    results = await asyncio.gather(*tasks)
    # flatten and deduplicate by event ID
    seen_ids = set()
    concerts = []

    for events in results:
        for event in events:
            event_id = event.get("id")
            if not event_id or event_id in seen_ids or not is_upcoming_event(event):
                continue
            seen_ids.add(event_id)
            concerts.append(event)

    # sort by date ascending: nearest concerts first
    return sorted(
        concerts,
        key=lambda e: e.get("date") or ""
    )
