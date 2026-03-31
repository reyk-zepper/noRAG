"""Info command — show noRAG store status and configuration."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from norag import __version__

console = Console()


def info_cmd(
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory (default: .norag)"),
) -> None:
    """Show noRAG store status, configuration, and knowledge stats."""
    from norag.config import load_config
    from norag.store import CKUStore, KnowledgeMap, AuditLog

    config = load_config()
    if store:
        config.store_dir = store
        config.ckus_dir = store / "ckus"
        config.db_path = store / "knowledge.db"
        config.audit_path = store / "audit.db"

    # Gather info
    cku_store = CKUStore(config.ckus_dir)
    cku_ids = cku_store.list_all()

    km = KnowledgeMap(config.db_path)
    stats = km.get_stats()

    audit = AuditLog(config.audit_path)
    audit_count = audit.count()

    info = (
        f"[bold]noRAG[/bold] v{__version__}\n"
        f"\n"
        f"[bold]Configuration[/bold]\n"
        f"  Store:    {config.store_dir}\n"
        f"  Provider: {config.provider}\n"
        f"  Model:    {config.model}\n"
        f"  Max Section Lines: {config.max_section_lines}\n"
        f"\n"
        f"[bold]Knowledge Store[/bold]\n"
        f"  CKUs:      {len(cku_ids)}\n"
        f"  Entities:  {stats.get('total_entities', 0)}\n"
        f"  Facts:     {stats.get('total_facts', 0)}\n"
        f"  Relations: {stats.get('total_relations', 0)}\n"
        f"  Topics:    {stats.get('total_topics', 0)}\n"
        f"\n"
        f"[bold]Audit Log[/bold]\n"
        f"  Events: {audit_count}"
    )

    console.print(Panel(info, title="noRAG Info", border_style="blue"))
