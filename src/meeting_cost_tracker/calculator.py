"""
Cost calculation engine for meetings.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .config import CostRates
from .graph_client import Meeting, MeetingAttendee


@dataclass
class MeetingCost:
    """Calculated cost for a meeting."""
    meeting: Meeting
    total_cost: float
    duration_hours: float
    attendee_count: int
    cost_breakdown: Dict[str, float]  # email -> cost
    unassigned_attendees: List[str]  # Emails without rates
    
    @property
    def cost_per_hour(self) -> float:
        """Calculate hourly cost rate for this meeting."""
        if self.duration_hours > 0:
            return self.total_cost / self.duration_hours
        return 0.0
    
    @property
    def cost_per_attendee_hour(self) -> float:
        """Calculate cost per attendee-hour."""
        attendee_hours = self.duration_hours * self.attendee_count
        if attendee_hours > 0:
            return self.total_cost / attendee_hours
        return 0.0


@dataclass
class CostAnalytics:
    """Aggregated cost analytics."""
    total_cost: float
    total_meetings: int
    total_meeting_hours: float
    total_attendee_hours: float
    average_meeting_cost: float
    average_meeting_duration: float
    average_attendees_per_meeting: float
    most_expensive_meetings: List[MeetingCost]
    top_attendees_by_cost: List[Tuple[str, float, int]]  # (email, total_cost, meeting_count)
    cost_by_day: Dict[str, float]  # date -> cost
    cost_by_org: Dict[str, float]  # domain -> cost
    potential_savings_30min: float  # If all meetings were 30 min
    potential_savings_15min: float  # If all meetings were 15 min shorter


class CostCalculator:
    """Calculate meeting costs based on configured rates."""
    
    def __init__(self, rates: CostRates):
        self.rates = rates
    
    def get_rate_for_attendee(self, attendee: MeetingAttendee) -> Optional[float]:
        """Determine hourly rate for an attendee.
        
        Tries in order:
        1. Per-person rate by email
        2. Role-based rate (if role info available)
        3. Organization rate by email domain
        4. Default rate
        """
        if not attendee.email:
            return self.rates.default_rate
        
        email_lower = attendee.email.lower()
        
        # Check per-person rate
        if email_lower in self.rates.person_rates:
            return self.rates.person_rates[email_lower]
        
        # Check organization rate by domain
        if "@" in email_lower:
            domain = email_lower.split("@")[1]
            if domain in self.rates.org_rates:
                return self.rates.org_rates[domain]
        
        # Default rate
        return self.rates.default_rate
    
    def calculate_meeting_cost(self, meeting: Meeting) -> MeetingCost:
        """Calculate cost for a single meeting."""
        duration_hours = meeting.duration_minutes / 60
        
        cost_breakdown = {}
        unassigned = []
        total_cost = 0.0
        
        # Cost for organizer
        if meeting.organizer:
            rate = self.get_rate_for_attendee(meeting.organizer)
            if rate:
                organizer_cost = rate * duration_hours
                cost_breakdown[meeting.organizer.email or "organizer"] = organizer_cost
                total_cost += organizer_cost
            else:
                unassigned.append(meeting.organizer.email or "organizer")
        
        # Cost for attendees
        for attendee in meeting.attendees:
            # Skip if declined
            if attendee.response_status == "declined":
                continue
            
            rate = self.get_rate_for_attendee(attendee)
            if rate:
                attendee_cost = rate * duration_hours
                email = attendee.email or attendee.name or f"attendee_{len(cost_breakdown)}"
                cost_breakdown[email] = cost_breakdown.get(email, 0) + attendee_cost
                total_cost += attendee_cost
            else:
                if attendee.email:
                    unassigned.append(attendee.email)
        
        # Count unique attendees (excluding organizer if also in attendees)
        attendee_count = len(meeting.attendees)
        if meeting.organizer:
            organizer_in_attendees = any(
                a.email and a.email.lower() == meeting.organizer.email.lower()
                for a in meeting.attendees if a.email
            )
            if not organizer_in_attendees:
                attendee_count += 1
        
        return MeetingCost(
            meeting=meeting,
            total_cost=total_cost,
            duration_hours=duration_hours,
            attendee_count=attendee_count,
            cost_breakdown=cost_breakdown,
            unassigned_attendees=unassigned,
        )
    
    def calculate_analytics(self, meeting_costs: List[MeetingCost]) -> CostAnalytics:
        """Calculate aggregated analytics from meeting costs."""
        if not meeting_costs:
            return CostAnalytics(
                total_cost=0.0,
                total_meetings=0,
                total_meeting_hours=0.0,
                total_attendee_hours=0.0,
                average_meeting_cost=0.0,
                average_meeting_duration=0.0,
                average_attendees_per_meeting=0.0,
                most_expensive_meetings=[],
                top_attendees_by_cost=[],
                cost_by_day={},
                cost_by_org={},
                potential_savings_30min=0.0,
                potential_savings_15min=0.0,
            )
        
        total_cost = sum(mc.total_cost for mc in meeting_costs)
        total_meetings = len(meeting_costs)
        total_meeting_hours = sum(mc.duration_hours for mc in meeting_costs)
        total_attendee_hours = sum(
            mc.duration_hours * mc.attendee_count for mc in meeting_costs
        )
        
        # Sort by cost for most expensive
        sorted_by_cost = sorted(meeting_costs, key=lambda x: x.total_cost, reverse=True)
        most_expensive = sorted_by_cost[:10]  # Top 10
        
        # Aggregate by attendee
        attendee_costs: Dict[str, Tuple[float, int]] = {}  # email -> (total_cost, meeting_count)
        for mc in meeting_costs:
            for email, cost in mc.cost_breakdown.items():
                current = attendee_costs.get(email, (0.0, 0))
                attendee_costs[email] = (current[0] + cost, current[1] + 1)
        
        top_attendees = sorted(
            [(email, cost, count) for email, (cost, count) in attendee_costs.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:10]  # Top 10
        
        # Cost by day
        cost_by_day: Dict[str, float] = {}
        for mc in meeting_costs:
            day = mc.meeting.start_time.strftime("%Y-%m-%d")
            cost_by_day[day] = cost_by_day.get(day, 0.0) + mc.total_cost
        
        # Cost by organization
        cost_by_org: Dict[str, float] = {}
        for mc in meeting_costs:
            for email in mc.cost_breakdown.keys():
                if "@" in email:
                    org = email.split("@")[1]
                    cost_by_org[org] = cost_by_org.get(org, 0.0) + mc.cost_breakdown[email]
        
        # Potential savings calculations
        potential_savings_30min = 0.0
        potential_savings_15min = 0.0
        
        for mc in meeting_costs:
            duration = mc.duration_hours
            cost_per_hour = mc.cost_per_hour
            attendee_count = mc.attendee_count
            
            # If meeting > 30 min, what if it was 30 min?
            if duration > 0.5:
                time_saved = duration - 0.5
                potential_savings_30min += cost_per_hour * time_saved
            
            # If meeting > 15 min, what if it was 15 min shorter?
            if duration > 0.25:
                time_saved = 0.25  # 15 minutes
                potential_savings_15min += cost_per_hour * time_saved
        
        return CostAnalytics(
            total_cost=total_cost,
            total_meetings=total_meetings,
            total_meeting_hours=total_meeting_hours,
            total_attendee_hours=total_attendee_hours,
            average_meeting_cost=total_cost / total_meetings,
            average_meeting_duration=sum(mc.duration_hours for mc in meeting_costs) / total_meetings,
            average_attendees_per_meeting=sum(mc.attendee_count for mc in meeting_costs) / total_meetings,
            most_expensive_meetings=most_expensive,
            top_attendees_by_cost=top_attendees,
            cost_by_day=cost_by_day,
            cost_by_org=cost_by_org,
            potential_savings_30min=potential_savings_30min,
            potential_savings_15min=potential_savings_15min,
        )
