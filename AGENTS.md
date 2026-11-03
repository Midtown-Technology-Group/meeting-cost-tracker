# Meeting Cost Tracker agent guidance

This Python CLI analyzes Microsoft Graph calendar events and estimates participant-time costs. `src/meeting_cost_tracker/` separates CLI/configuration, Graph access, cost calculation, and reporting. Read [README.md](README.md), [SECURITY.md](SECURITY.md), and the declared entry points in `pyproject.toml` before changes.

## Working and verification

Use Python 3.10+ and `python -m pip install -e ".[dev]"` for the declared development environment. Check `mct --help` from an installed package for CLI changes; do not invoke `mct analyze` as a harmless smoke test because it can authenticate and read a real calendar. Exercise calculations and reporting with synthetic meetings and rates instead.

No test files or pytest configuration were found in the current default tree, despite pytest being a dev dependency. Do not report `pytest` as an established passing gate. For behavior changes, add focused tests of duration, attendee/rate matching, date ranges, aggregation, and export at the production seam, then document the check actually run. Existing release and Sonar workflows are not a substitute for those behavioral tests.

## Privacy and release boundaries

Require a user-configured client ID; retain `common` as the tenant default for multi-tenant use. Never introduce shared credential defaults. Preserve least-privilege calendar access, user-only token-cache permissions, confidential per-person rates, and secure report storage. Do not commit tokens, cost models, real attendee lists, or reports. Calculations are estimates from configured rates, not verified payroll costs. The security page documents a filesystem-protected token cache; do not claim encryption without inspecting implementation.

CLI options must be verified in `cli.py`; documentation alone is insufficient. Export and analysis are distinct read/write surfaces. Inspect the Windows MSI workflow and build script before tag/release work; publishing, installation, or live Graph access requires the exact authorized scope.

## Secret gate before publication

Before publishing the current PR branch, commit the complete candidate and run
`python3 scripts/secret_gate.py --base origin/master` (native Windows: `python`). Require exit 0;
missing tooling/authentication, scan errors and skipped scans block publication.
Then run the existing repository gates. Repeat after changing outgoing commits.
Push exactly the scanned HEAD. This PR scan covers the current branch against its
fetched intended base; other refs, multi-ref pushes and rewritten history require
`--pre-push` with Git's complete ref-update stream. Stop if any pushed ref is
uncovered. See [secret scanning](SECRET-SCANNING.md) for base selection, new branches,
pre-push input and prerequisites. Preserve GitGuardian App, CI and Gitleaks checks.

For a non-default PR target, fetch its destination and pass that exact ref to
`--base`; the remote default is not a substitute for a release/maintenance base.

The secret gate requires Python 3.11+ and approved ggshield >=1.56.1,<2.
