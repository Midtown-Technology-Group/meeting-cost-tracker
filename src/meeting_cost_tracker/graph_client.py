"""
Microsoft Graph client for meeting data retrieval.

Leverages work-context-sync patterns for authentication.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions
from msgraph import GraphServiceClient
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.users.item.calendar_view.calendar_view_request_builder import CalendarViewRequestBuilder


@dataclass
class MeetingAttendee:
    """Represents a meeting attendee."""
    email: Optional[str]
    name: Optional[str]
    response_status: str  # accepted, tentative, declined, none
    is_organizer: bool = False
    is_optional: bool = False


@dataclass
class Meeting:
    """Represents a calendar meeting."""
    id: str
    subject: str
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    organizer: Optional[MeetingAttendee]
    attendees: List[MeetingAttendee]
    is_recurring: bool
    location: Optional[str]
    is_online_meeting: bool


class GraphMeetingClient:
    """Microsoft Graph client for meeting data."""
    
    SCOPES = ["Calendars.Read", "User.Read", "MailboxSettings.Read"]
    
    def __init__(self, tenant_id: str = "common", client_id: Optional[str] = None):
        """Initialize Graph client.
        
        Args:
            tenant_id: Azure AD tenant ID (default: common for multi-tenant apps)
            client_id: Azure AD app client ID. If None, uses default app.
        """
        self.tenant_id = tenant_id
        if not client_id:
            raise ValueError(
                "client_id is required. Set it in ~/.meeting-cost-tracker/config.yaml "
                "or environment variable MEETING_COST_TRACKER_CLIENT_ID"
            )
        self.client_id = client_id
        self._client: Optional[GraphServiceClient] = None
        
    def _get_token_cache_path(self) -> Path:
        """Get path for token cache."""
        cache_dir = Path.home() / ".meeting-cost-tracker" / "tokens"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "token_cache.json"
    
    def _authenticate(self) -> GraphServiceClient:
        """Authenticate and return Graph client."""
        if self._client:
            return self._client
        
        cache_path = self._get_token_cache_path()
        
        persistence_options = TokenCachePersistenceOptions(
            name="meeting_cost_tracker",
            allow_unencrypted_storage=False,
        )
        
        credential = DeviceCodeCredential(
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            cache_persistence_options=persistence_options,
            prompt_callback=self._device_code_callback,
        )
        
        self._client = GraphServiceClient(credentials=credential, scopes=self.SCOPES)
        return self._client
    
    def _device_code_callback(self, user_code: str, verification_uri: str, expires_in: int):
        """Display device code for user authentication."""
        print(f"\n🔐 Authentication required")
        print(f"   Please visit: {verification_uri}")
        print(f"   Enter code: {user_code}")
        print(f"   Expires in {expires_in} seconds\n")
    
    async def get_meetings(
        self,
        start_date: datetime,
        end_date: datetime,
        include_attendees: bool = True,
    ) -> List[Meeting]:
        """Get meetings from calendar.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            include_attendees: Whether to fetch attendee details
            
        Returns:
            List of Meeting objects
        """
        client = self._authenticate()
        
        # Format dates for Graph API
        if start_date.tzinfo is None:
            start_date = start_date.astimezone()
        if end_date.tzinfo is None:
            end_date = end_date.astimezone()
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # Calendar view expands recurring meetings within the requested range.
        request_builder = client.me.calendar_view
        query_params = CalendarViewRequestBuilder.CalendarViewRequestBuilderGetQueryParameters(
            start_date_time=start_str,
            end_date_time=end_str,
            select=["id", "subject", "start", "end", "organizer", "attendees", 
                   "isOnlineMeeting", "onlineMeeting", "location", "recurrence"],
            top=500,  # Max per page
        )
        
        request_config = RequestConfiguration(query_parameters=query_params)
        response = await request_builder.get(request_configuration=request_config)

        meetings = []
        requested_links = set()
        while response:
            for event in response.value or []:
                meetings.append(self._parse_event(event))
            if not response.odata_next_link:
                break
            if response.odata_next_link in requested_links:
                raise ValueError("Repeated calendar pagination link")
            requested_links.add(response.odata_next_link)
            response = await request_builder.with_url(response.odata_next_link).get()
        
        return meetings
    
    def _parse_event(self, event) -> Meeting:
        """Parse Graph event into Meeting dataclass."""
        # Parse start/end times
        start = event.start
        end = event.end
        
        start_time = self._parse_datetime(start.date_time if hasattr(start, 'date_time') else start)
        end_time = self._parse_datetime(end.date_time if hasattr(end, 'date_time') else end)
        
        duration = (end_time - start_time).total_seconds() / 60
        
        # Parse organizer
        organizer = None
        if event.organizer and event.organizer.email_address:
            organizer = MeetingAttendee(
                email=event.organizer.email_address.address,
                name=event.organizer.email_address.name,
                response_status="organizer",
                is_organizer=True,
            )
        
        # Parse attendees
        attendees = []
        if event.attendees:
            for attendee in event.attendees:
                email = None
                name = None
                if attendee.email_address:
                    email = attendee.email_address.address
                    name = attendee.email_address.name
                
                attendees.append(MeetingAttendee(
                    email=email,
                    name=name,
                    response_status=attendee.status.response if attendee.status else "none",
                    is_optional=attendee.type == "optional",
                ))
        
        # Check if online meeting
        is_online = False
        if hasattr(event, 'is_online_meeting'):
            is_online = event.is_online_meeting or False
        if hasattr(event, 'online_meeting') and event.online_meeting:
            is_online = True
        
        # Get location
        location = None
        if event.location:
            location = event.location.display_name
        
        return Meeting(
            id=event.id,
            subject=event.subject or "(No subject)",
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            organizer=organizer,
            attendees=attendees,
            is_recurring=event.recurrence is not None,
            location=location,
            is_online_meeting=is_online,
        )
    
    def _parse_datetime(self, dt) -> datetime:
        """Parse datetime from Graph response."""
        if isinstance(dt, datetime):
            return dt
        if isinstance(dt, str):
            # Try ISO format
            return datetime.fromisoformat(dt.replace('Z', '+00:00'))
        raise ValueError(f"Cannot parse datetime: {dt}")


def create_graph_client(tenant_id: str = "common", client_id: Optional[str] = None) -> GraphMeetingClient:
    """Factory function to create Graph client."""
    return GraphMeetingClient(tenant_id=tenant_id, client_id=client_id)
