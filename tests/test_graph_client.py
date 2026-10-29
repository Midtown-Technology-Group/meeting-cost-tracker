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


class LocalDateTime(datetime):
    def astimezone(self, tz=None):
        from datetime import timedelta

        return self.replace(tzinfo=timezone(timedelta(hours=-4)))


def test_naive_bounds_receive_local_offsets():
    from meeting_cost_tracker.graph_client import GraphMeetingClient

    calendar_view = SimpleNamespace(get=AsyncMock(return_value=None))
    client = GraphMeetingClient(client_id="offline-test")
    client._client = SimpleNamespace(me=SimpleNamespace(calendar_view=calendar_view))
    asyncio.run(client.get_meetings(LocalDateTime(2026, 10, 1), LocalDateTime(2026, 10, 2)))
    query = calendar_view.get.call_args.kwargs["request_configuration"].query_parameters
    assert query.start_date_time == "2026-10-01T00:00:00-04:00"
    assert query.end_date_time == "2026-10-02T00:00:00-04:00"


def test_aware_bounds_preserve_supplied_offsets():
    from datetime import timedelta

    from meeting_cost_tracker.graph_client import GraphMeetingClient

    calendar_view = SimpleNamespace(get=AsyncMock(return_value=None))
    client = GraphMeetingClient(client_id="offline-test")
    client._client = SimpleNamespace(me=SimpleNamespace(calendar_view=calendar_view))
    offset = timezone(timedelta(hours=5, minutes=30))
    start = LocalDateTime(2026, 10, 1, tzinfo=offset)
    end = LocalDateTime(2026, 10, 2, tzinfo=offset)
    asyncio.run(client.get_meetings(start, end))
    query = calendar_view.get.call_args.kwargs["request_configuration"].query_parameters
    assert query.start_date_time == "2026-10-01T00:00:00+05:30"
    assert query.end_date_time == "2026-10-02T00:00:00+05:30"


def test_pagination_cycle_raises_instead_of_returning_partial_results():
    import pytest

    from meeting_cost_tracker.graph_client import GraphMeetingClient

    link = "https://graph.microsoft.com/v1.0/me/calendarView?$skiptoken=repeat"
    page = EventCollectionResponse(value=[], odata_next_link=link)
    calendar_view = SimpleNamespace(get=AsyncMock(side_effect=[page, page, None]))
    calendar_view.with_url = Mock(return_value=calendar_view)
    client = GraphMeetingClient(client_id="offline-test")
    client._client = SimpleNamespace(me=SimpleNamespace(calendar_view=calendar_view))
    with pytest.raises(ValueError, match="Repeated calendar pagination link"):
        asyncio.run(client.get_meetings(datetime(2026, 10, 1), datetime(2026, 10, 2)))
    assert calendar_view.get.await_count == 2
