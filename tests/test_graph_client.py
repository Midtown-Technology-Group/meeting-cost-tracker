"""Offline regression checks against the installed Graph SDK."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from msgraph import GraphServiceClient
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.event import Event
from msgraph.generated.models.event_collection_response import EventCollectionResponse


def test_calendar_view_uses_date_range_and_follows_pages():
    from meeting_cost_tracker.graph_client import GraphMeetingClient

    adapter = Mock()
    adapter.base_url = "https://graph.microsoft.com/v1.0"
    event = Event(
        id="synthetic",
        subject="Offline meeting",
        start=DateTimeTimeZone(date_time="2026-10-01T10:00:00", time_zone="UTC"),
        end=DateTimeTimeZone(date_time="2026-10-01T11:00:00", time_zone="UTC"),
    )
    next_link = "https://graph.microsoft.com/v1.0/me/calendarView?$skiptoken=synthetic"
    adapter.send_async = AsyncMock(
        side_effect=[
            EventCollectionResponse(value=[event], odata_next_link=next_link),
            EventCollectionResponse(value=[event]),
        ]
    )
    client = GraphMeetingClient(client_id="offline-test")
    client._client = GraphServiceClient(request_adapter=adapter)
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 2, tzinfo=timezone.utc)

    meetings = asyncio.run(client.get_meetings(start, end))

    assert len(meetings) == 2
    assert meetings[0].duration_minutes == 60
    first_request = adapter.send_async.call_args_list[0].args[0]
    assert "/calendarView" in first_request.url
    assert "startDateTime=2026-10-01T00%3A00%3A00%2B00%3A00" in first_request.url
    assert "endDateTime=2026-10-02T00%3A00%3A00%2B00%3A00" in first_request.url
    assert adapter.send_async.call_args_list[1].args[0].url == next_link


def test_empty_calendar_view():
    from meeting_cost_tracker.graph_client import GraphMeetingClient

    calendar_view = SimpleNamespace(get=AsyncMock(return_value=None))
    client = GraphMeetingClient(client_id="offline-test")
    client._client = SimpleNamespace(me=SimpleNamespace(calendar_view=calendar_view))
    assert asyncio.run(client.get_meetings(datetime(2026, 10, 1), datetime(2026, 10, 2))) == []
