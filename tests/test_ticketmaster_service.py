from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.services import ticketmaster_service


# Builds normalized event dicts around today's date
def build_event(event_id: str, days_from_now: int) -> dict:
    event_date = (datetime.now(timezone.utc).date() + timedelta(days=days_from_now)).isoformat()
    return {
        "id": event_id,
        "name": f"Artist One - Event {event_id}",
        "artist": "Artist One",
        "date": event_date,
        "local_date": event_date,
    }


# Cached Ticketmaster events should still be filtered by current date
async def test_get_artist_events_filters_past_cached_events():
    past_event = build_event("past", -1)
    future_event = build_event("future", 5)

    with patch("app.services.ticketmaster_service.cache_get", new=AsyncMock(return_value=[past_event, future_event])):
        events = await ticketmaster_service.get_artist_events("Artist One")

    assert events == [future_event]


# Ticketmaster API requests should ask only for upcoming events
async def test_get_artist_events_sends_start_datetime_to_ticketmaster():
    captured_params = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"_embedded": {"events": []}}

    # Minimal async client stub used instead of the shared httpx client
    class FakeClient:
        async def get(self, url, params):
            captured_params.update(params)
            return FakeResponse()

    with patch("app.services.ticketmaster_service.cache_get", new=AsyncMock(return_value=None)), \
         patch("app.services.ticketmaster_service.cache_set", new=AsyncMock()), \
         patch("app.services.ticketmaster_service.get_http_client", return_value=FakeClient()):
        events = await ticketmaster_service.get_artist_events("Artist One")

    assert events == []
    assert "startDateTime" in captured_params
    assert captured_params["startDateTime"].endswith("Z")


# Final concert aggregation also filters past events
async def test_get_concerts_for_artists_filters_past_events_after_dedupe():
    past_event = build_event("past", -2)
    future_event = build_event("future", 10)

    with patch("app.services.ticketmaster_service.get_artist_events", new=AsyncMock(return_value=[past_event, future_event])):
        concerts = await ticketmaster_service.get_concerts_for_artists(["Artist One"])

    assert concerts == [future_event]


# Venues reported at 0,0 have no real location and must not land on the map
def test_map_ticketmaster_event_treats_zero_coordinates_as_missing():
    event = {
        "id": "evt-1",
        "_embedded": {"venues": [{"location": {"latitude": "0", "longitude": "0"}}]},
    }

    mapped = ticketmaster_service.map_ticketmaster_event(event, "Artist One")

    assert mapped["lat"] is None
    assert mapped["lng"] is None


def test_map_ticketmaster_event_keeps_real_coordinates():
    event = {
        "id": "evt-2",
        "_embedded": {"venues": [{"location": {"latitude": "52.2297", "longitude": "21.0122"}}]},
    }

    mapped = ticketmaster_service.map_ticketmaster_event(event, "Artist One")

    assert mapped["lat"] == 52.2297
    assert mapped["lng"] == 21.0122


# Keyword search returns other acts sharing a word; only events naming the artist stay
def test_filter_artist_events_drops_other_acts_and_keeps_tributes():
    titles = {
        "tribute": "Message In A Bottle - The Police Tribute",
        "celebration": "The Sister Moon Project: Celebrating the music of Sting & The Police",
        "other_act": "Police Dog Hogan - Hertford Corn Exchange",
        "other_tribute": "KARMA POLICE: TRIBUTE TO RADIOHEAD",
        "shared_word": "Joan As Police Woman",
    }
    events = [{"id": key, "name": title, "performers": []} for key, title in titles.items()]

    kept = ticketmaster_service.filter_artist_events(events, "The Police")

    assert [event["id"] for event in kept] == ["tribute", "celebration"]


# Festival titles often skip the artist, so the performer list counts too
def test_filter_artist_events_matches_performers_and_ignores_accents():
    festival = {"id": "fest", "name": "Open'er Festival 2027", "performers": ["Beyoncé", "Sigur Rós"]}

    assert ticketmaster_service.filter_artist_events([festival], "Sigur Ros") == [festival]
    assert ticketmaster_service.filter_artist_events([festival], "Beyonce") == [festival]
    assert ticketmaster_service.filter_artist_events([festival], "Beyonce Knowles") == []
    assert ticketmaster_service.filter_artist_events([festival], "Sigu") == []


# Corona, CA arrives from Ticketmaster with a positive longitude, which lands in China
def test_check_event_coordinates_restores_dropped_minus_sign():
    event = {"id": "corona", "country": "US", "lat": 33.8511, "lng": 117.55648}

    assert ticketmaster_service.check_event_coordinates(event) == {**event, "lng": -117.55648}


def test_check_event_coordinates_fixes_swapped_lat_lng():
    event = {"id": "warsaw", "country": "PL", "lat": 21.0122, "lng": 52.2297}

    checked = ticketmaster_service.check_event_coordinates(event)

    assert (checked["lat"], checked["lng"]) == (52.2297, 21.0122)


def test_check_event_coordinates_drops_unfixable_points_and_keeps_good_ones():
    broken = {"id": "broken", "country": "GB", "lat": 10.0, "lng": 100.0}
    good = {"id": "good", "country": "GB", "lat": 51.5072, "lng": -0.1276}
    unknown_country = {"id": "other", "country": "BR", "lat": -23.55, "lng": -46.63}

    assert ticketmaster_service.check_event_coordinates(broken)["lat"] is None
    assert ticketmaster_service.check_event_coordinates(good) == good
    assert ticketmaster_service.check_event_coordinates(unknown_country) == unknown_country
