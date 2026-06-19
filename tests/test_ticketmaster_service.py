from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.services import ticketmaster_service


def build_event(event_id: str, days_from_now: int) -> dict:
    event_date = (datetime.now(timezone.utc).date() + timedelta(days=days_from_now)).isoformat()
    return {
        "id": event_id,
        "name": f"Event {event_id}",
        "artist": "Artist One",
        "date": event_date,
        "local_date": event_date,
    }


async def test_get_artist_events_filters_past_cached_events():
    past_event = build_event("past", -1)
    future_event = build_event("future", 5)

    with patch("app.services.ticketmaster_service.cache_get", new=AsyncMock(return_value=[past_event, future_event])):
        events = await ticketmaster_service.get_artist_events("Artist One")

    assert events == [future_event]


async def test_get_artist_events_sends_start_datetime_to_ticketmaster():
    captured_params = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"_embedded": {"events": []}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, params, timeout):
            captured_params.update(params)
            return FakeResponse()

    with patch("app.services.ticketmaster_service.cache_get", new=AsyncMock(return_value=None)), \
         patch("app.services.ticketmaster_service.cache_set", new=AsyncMock()), \
         patch("app.services.ticketmaster_service.httpx.AsyncClient", return_value=FakeClient()):
        events = await ticketmaster_service.get_artist_events("Artist One")

    assert events == []
    assert "startDateTime" in captured_params
    assert captured_params["startDateTime"].endswith("Z")


async def test_get_concerts_for_artists_filters_past_events_after_dedupe():
    past_event = build_event("past", -2)
    future_event = build_event("future", 10)

    with patch("app.services.ticketmaster_service.get_artist_events", new=AsyncMock(return_value=[past_event, future_event])):
        concerts = await ticketmaster_service.get_concerts_for_artists(["Artist One"])

    assert concerts == [future_event]
