import asyncio
import logging
import httpx
from app.core.cache import cache_get, cache_set
from app.core.config import settings
logger = logging.getLogger(__name__)
TICKETMASTER_BASE = "https://app.ticketmaster.com/discovery/v2"
TICKETMASTER_CACHE_TTL_SECONDS = 60 * 60 * 12
TICKETMASTER_CACHE_VERSION = "v2"


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


def map_ticketmaster_event(event: dict, artist_name: str) -> dict:
    """
    Maps raw Ticketmaster event data to the fields the app needs
    """
    venue = {}
    venues = event.get("_embedded", {}).get("venues", [])
    if venues:
        venue = venues[0]

    images = event.get("images", [])
    image_url = images[0].get("url") if images else None

    start = event.get("dates", {}).get("start", {})
    city = venue.get("city", {})
    country = venue.get("country", {})
    location = venue.get("location", {})

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
        "lat": parse_coordinate(location.get("latitude")),
        "lng": parse_coordinate(location.get("longitude")),
        "image_url": image_url,
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
        return cached_events

    params = {
        "apikey": settings.TICKETMASTER_API_KEY,
        "keyword": artist_name,
        "classificationName": "music",  # only music events
        "sort": "date,asc",             # nearest concerts first
        "size": 10,
    }

    if country_code:
        params["countryCode"] = country_code

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TICKETMASTER_BASE}/events.json",
                params=params,
                timeout=10.0,
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
        events = [map_ticketmaster_event(event, artist_name) for event in raw_events]
        await cache_set(cache_key, events, ttl_seconds=TICKETMASTER_CACHE_TTL_SECONDS)
        return events

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
            if not event_id or event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            concerts.append(event)

    # sort by date ascending: nearest concerts first
    return sorted(
        concerts,
        key=lambda e: e.get("date") or ""
    )
