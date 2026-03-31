"""Audit command — view the noRAG audit log."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def audit_cmd(
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory (default: .norag)"),
    event_type: str = typer.Option(None, "--type", "-t", help="Filter by event type: compile | query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of events to show"),
) -> None:
    """Show the audit log — who compiled/queried what, when."""
    from norag.config import load_config
    from norag.store import AuditLog

    config = load_config()
    if store:
        config.store_dir = store
        config.audit_path = store / "audit.db"

    audit = AuditLog(config.audit_path)
    events = audit.list_events(event_type=event_type, limit=limit)
    total = audit.count(event_type=event_type)

    if not events:
        console.print("[yellow]No audit events found.[/yellow]")
        return

    table = Table(title=f"Audit Log ({total} total)")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Time", width=20)
    table.add_column("Event", width=8)
    table.add_column("User", width=12)
    table.add_column("Details")

    for event in events:
        details = event["details"]
        if event["event"] == "compile":
            detail_str = f"{details.get('source', '?')} → {details.get('status', '?')}"
            roles = details.get("roles", [])
            if roles:
                detail_str += f" [roles: {', '.join(roles)}]"
        elif event["event"] == "query":
            q = details.get("question", "?")
            detail_str = f'"{q[:60]}{"…" if len(q) > 60 else ""}"'
            sources = details.get("sources", [])
            if sources:
                detail_str += f" → {len(sources)} source(s)"
        else:
            detail_str = str(details)[:80]

        timestamp = event["timestamp"][:19].replace("T", " ")

        table.add_row(
            str(event["id"]),
            timestamp,
            event["event"],
            event["user"] or "—",
            detail_str,
        )

    console.print(table)
