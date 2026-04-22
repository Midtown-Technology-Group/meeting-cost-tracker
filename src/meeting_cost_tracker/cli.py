"""
CLI interface for Meeting Cost Tracker.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .config import load_config
from .graph_client import create_graph_client, Meeting
from .calculator import CostCalculator, MeetingCost, CostAnalytics
from .reporter import ConsoleReporter, ExcelReporter

app = typer.Typer(
    name="mct",
    help="Track the real cost of Microsoft Teams meetings",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        rprint(f"[bold blue]meeting-cost-tracker[/bold blue] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """Meeting Cost Tracker - Calculate the real cost of your meetings."""
    pass


@app.command()
def analyze(
    start: Optional[str] = typer.Option(
        None, "--start", "-s",
        help="Start date (YYYY-MM-DD, default: 30 days ago)",
    ),
    end: Optional[str] = typer.Option(
        None, "--end", "-e",
        help="End date (YYYY-MM-DD, default: today)",
    ),
    weeks: Optional[int] = typer.Option(
        None, "--weeks", "-w",
        help="Analyze last N weeks (alternative to --start/--end)",
    ),
    rate: Optional[float] = typer.Option(
        None, "--rate", "-r",
        help="Override default hourly rate (USD)",
    ),
    export: Optional[str] = typer.Option(
        None, "--export", "-o",
        help="Export to file (CSV or Excel)",
    ),
    top: int = typer.Option(
        10, "--top", "-t",
        help="Show top N most expensive meetings",
    ),
    savings: bool = typer.Option(
        False, "--savings",
        help="Show potential savings analysis",
    ),
):
    """Analyze meeting costs for a date range.
    
    Examples:
        mct analyze --weeks 4
        mct analyze --start 2026-01-01 --end 2026-01-31
        mct analyze --weeks 2 --rate 150 --export report.xlsx
    """
    # Parse dates
    if weeks:
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
    else:
        if end:
            end_date = datetime.strptime(end, "%Y-%m-%d")
        else:
            end_date = datetime.now()
        
        if start:
            start_date = datetime.strptime(start, "%Y-%m-%d")
        else:
            start_date = end_date - timedelta(days=30)
    
    # Load config
    config = load_config()
    if rate:
        config.costs.default_rate = rate
    
    # Run async analysis
    asyncio.run(_run_analysis(start_date, end_date, config, export, top, savings))


async def _run_analysis(
    start_date: datetime,
    end_date: datetime,
    config,
    export_path: Optional[str],
    top_n: int,
    show_savings: bool,
):
    """Run the async analysis workflow."""
    calculator = CostCalculator(config.costs)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching meetings from Microsoft Graph...", total=None)
        
        # Get meetings
        graph_client = create_graph_client()
        meetings = await graph_client.get_meetings(start_date, end_date)
        
        progress.update(task, description=f"Processing {len(meetings)} meetings...")
        
        # Calculate costs
        meeting_costs = [calculator.calculate_meeting_cost(m) for m in meetings]
        analytics = calculator.calculate_analytics(meeting_costs)
        
        progress.update(task, visible=False)
    
    # Display results
    reporter = ConsoleReporter(console)
    reporter.display_summary(analytics)
    reporter.display_top_meetings(analytics.most_expensive_meetings[:top_n])
    reporter.display_top_attendees(analytics.top_attendees_by_cost[:10])
    
    if show_savings:
        reporter.display_savings(analytics)
    
    # Export if requested
    if export_path:
        if export_path.endswith('.xlsx'):
            excel_reporter = ExcelReporter()
            excel_reporter.export(analytics, meeting_costs, export_path)
        else:
            # CSV export
            _export_csv(meeting_costs, export_path)
        rprint(f"\n[green]✓ Exported to {export_path}[/green]")


def _export_csv(meeting_costs: list, path: str):
    """Export meeting costs to CSV."""
    import csv
    
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Date', 'Subject', 'Duration (min)', 'Attendees', 
            'Total Cost', 'Cost per Hour'
        ])
        for mc in meeting_costs:
            writer.writerow([
                mc.meeting.start_time.strftime("%Y-%m-%d"),
                mc.meeting.subject,
                mc.meeting.duration_minutes,
                mc.attendee_count,
                f"${mc.total_cost:.2f}",
                f"${mc.cost_per_hour:.2f}",
            ])


@app.command()
def config():
    """Show current cost configuration."""
    cfg = load_config()
    
    rprint(Panel(
        f"[bold]Default Rate:[/bold] ${cfg.costs.default_rate:.2f}/hr\n"
        f"[bold]Per-Person Rates:[/bold] {len(cfg.costs.person_rates)} configured\n"
        f"[bold]Role-Based Rates:[/bold] {len(cfg.costs.role_rates)} roles\n"
        f"[bold]Org Rates:[/bold] {len(cfg.costs.org_rates)} domains\n\n"
        f"[dim]Config file:[/dim] ~/.meeting-cost-tracker/config.yaml",
        title="Cost Configuration",
        border_style="cyan",
    ))
    
    if cfg.costs.person_rates:
        rprint("\n[bold]Per-Person Rates:[/bold]")
        for email, rate in sorted(cfg.costs.person_rates.items()):
            rprint(f"  {email}: ${rate:.2f}/hr")
    
    if cfg.costs.role_rates:
        rprint("\n[bold]Role-Based Rates:[/bold]")
        for role, rate in sorted(cfg.costs.role_rates.items()):
            rprint(f"  {role}: ${rate:.2f}/hr")


def cli_main():
    """Entry point for CLI."""
    app()
