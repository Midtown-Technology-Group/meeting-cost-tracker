# Meeting Cost Tracker agent guidance

This Python CLI analyzes Microsoft Graph calendar events and estimates participant-time costs. `src/meeting_cost_tracker/` separates CLI/configuration, Graph access, cost calculation, and reporting. Read [README.md](README.md), [SECURITY.md](SECURITY.md), and the declared entry points in `pyproject.toml` before changes.

## Working and verification

Use Python 3.10+ and `python -m pip install -e ".[dev]"` for the declared development environment. Check `mct --help` from an installed package for CLI changes; do not invoke `mct analyze` as a harmless smoke test because it can authenticate and read a real calendar. Exercise calculations and reporting with synthetic meetings and rates instead.

No test files or pytest configuration were found in the current default tree, despite pytest being a dev dependency. Do not report `pytest` as an established passing gate. For behavior changes, add focused tests of duration, attendee/rate matching, date ranges, aggregation, and export at the production seam, then document the check actually run. Existing release and Sonar workflows are not a substitute for those behavioral tests.

## Privacy and release boundaries

Require a user-configured client ID; retain `common` as the tenant default for multi-tenant use. Never introduce shared credential defaults. Preserve least-privilege calendar access, user-only token-cache permissions, confidential per-person rates, and secure report storage. Do not commit tokens, cost models, real attendee lists, or reports. Calculations are estimates from configured rates, not verified payroll costs. The security page documents a filesystem-protected token cache; do not claim encryption without inspecting implementation.

CLI options must be verified in `cli.py`; documentation alone is insufficient. Export and analysis are distinct read/write surfaces. Inspect the Windows MSI workflow and build script before tag/release work; publishing, installation, or live Graph access requires the exact authorized scope.
