import asyncio
import logging
import httpx
from app.core.config import settings
logger = logging.getLogger(__name__)
TICKETMASTER_BASE = "https://app.ticketmaster.com/discovery/v2"


async def get_artist_events(artist_name: str, country_code: str | None = None) -> list[dict]:
    """
    Gets upcoming music events for a given artist from Ticketmaster
    Optionally filters by country code (ISO 3166, e.g. 'PL', 'GB', 'US')
    Returns empty list if artist not found or no upcoming events
    """
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
        return data.get("_embedded", {}).get("events", [])

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
        key=lambda e: e.get("dates", {}).get("start", {}).get("dateTime", "")
    )