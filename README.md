# Meeting Cost Tracker

Track the real cost of Microsoft Teams meetings by calculating participant time × hourly rates.

## Installation

```bash
pip install meeting-cost-tracker
```

## Quick Start

```bash
# Analyze last 4 weeks
mct analyze --weeks 4

# Custom date range
mct analyze --start 2026-01-01 --end 2026-01-31

# Override default rate
mct analyze --weeks 2 --rate 150

# Export to Excel
mct analyze --weeks 4 --export report.xlsx

# Show savings opportunities
mct analyze --weeks 4 --savings
```

## Configuration

Create `~/.meeting-cost-tracker/config.yaml`:

```yaml
costs:
  default_rate: 100.0  # Default hourly rate
  
  # Per-person rates
  person_rates:
    john.smith@company.com: 150.0
    jane.doe@company.com: 200.0
  
  # Role-based rates
  role_rates:
    engineer: 100.0
    senior_engineer: 125.0
    manager: 150.0
    director: 200.0
    c_level: 300.0
  
  # Organization rates (by email domain)
  org_rates:
    company.com: 125.0
    client.com: 150.0
```

## Features

- 📊 **Cost Analysis**: Calculates meeting costs based on duration × attendees × hourly rate
- 🔍 **Microsoft Graph Integration**: Pulls calendar data from your Outlook/Teams
- 💰 **Flexible Cost Models**: Per-person, role-based, or organization rates
- 📈 **Analytics**: Top expensive meetings, attendees by cost, daily trends
- 💡 **Savings Analysis**: "What if meetings were 30 min or 15 min shorter?"
- 📤 **Export**: CSV or Excel with charts
- 🔒 **Privacy**: Only accesses your calendar, no data leaves your machine

## Cost Calculation

Formula: `Meeting Cost = Duration (hours) × Sum of attendee hourly rates`

Example: A 60-minute meeting with 8 people at $150/hr = **$1,800**

## License

AGPL-3.0
