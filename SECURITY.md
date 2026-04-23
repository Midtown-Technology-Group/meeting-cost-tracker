# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Active |

## Reporting Security Issues

Email: **security@midtowntg.com**

## Credentials & Configuration

### Microsoft Graph Authentication

This tool requires Microsoft Graph API access to read calendar events for cost calculation.

### Required Configuration

Create `~/.meeting-cost-tracker/config.yaml`:

```yaml
azure:
  tenant_id: "your-tenant-id"
  client_id: "your-client-id"  # Required - no default
  
cost_model:
  default_hourly_rate: 150.00
  currency: "USD"
```

**Important:** You must provide your own client_id. There is no default - this prevents accidental use of shared credentials.

### Getting Credentials

1. Go to [Azure Portal](https://portal.azure.com) → Azure AD → App registrations
2. New registration: Name it "Meeting Cost Tracker"
3. Supported account types: Accounts in this organizational directory only
4. Copy the **Application (client) ID** and **Directory (tenant) ID**
5. Add Microsoft Graph permission: `Calendars.Read`
6. Grant admin consent

### Authentication Flow

This tool uses **Device Code Flow** by default:
1. Run the tool
2. It displays a device code
3. Visit https://microsoft.com/devicelogin and enter the code
4. Sign in with your work account
5. Token is cached for future runs

### Token Storage

- **Location**: `~/.meeting-cost-tracker/tokens/token_cache.json`
- **Encryption**: File system permissions only (user-only access)
- **For better security**: Use context-sync's DPAPI encryption pattern (see docs)

## Data Handling

### What Data is Accessed

- **Calendar Events**: Subject, start/end time, attendees list
- **Attendee Details**: Email addresses for cost model matching
- **No Access To**: Email body, chat messages, file content

### Data Storage

All cost calculations are stored locally:
- Reports: `~/Documents/MeetingCostReports/` (configurable)
- Cache: `~/.meeting-cost-tracker/`
- No cloud storage or third-party services

### Privacy

- Attendee emails are hashed in logs
- Meeting subjects can be masked with `--mask-subjects`
- All processing happens locally after data retrieval

## Least Privilege

Required Graph API permissions:

| Permission | Purpose | Admin Consent |
|------------|---------|---------------|
| `Calendars.Read` | Read meeting times and attendees | Yes |
| `User.ReadBasic.All` | Resolve attendee names | Yes |

## Security Best Practices

1. **Config file permissions**: Set to user-only (0600)
2. **Token cache**: Don't share between users
3. **Cost models**: Keep `cost_rates.yaml` confidential (contains salary info)
4. **Reports**: Store in secure location - may contain organizational data

## Input Validation

- Date formats strictly validated (ISO 8601)
- Cost rates validated as positive numbers
- Attendee emails validated for format
- No shell execution of user input

## Development

When contributing:
1. Never commit `config.yaml` or `cost_rates.yaml`
2. Use example configs as templates
3. Test with mock data, not production calendars
4. Run `bandit -r src/` before submitting
