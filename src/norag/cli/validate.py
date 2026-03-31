"""Validate command — check CKU files against the schema."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def validate_cmd(
    target: Path = typer.Argument(
        None, help="CKU file or store directory to validate (default: .norag/ckus)"
    ),
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory"),
) -> None:
    """Validate CKU YAML files against the schema.

    Checks that all CKU files are well-formed and conform to the CKU Spec v1.
    """
    from norag.config import load_config
    from norag.models.cku import CKU

    config = load_config()
    if store:
        config.store_dir = store
        config.ckus_dir = store / "ckus"

    # Determine files to validate
    if target is None:
        target = config.ckus_dir

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.glob("*.yaml"))
    else:
        console.print(f"[red]Error:[/red] Not found: {target}")
        raise typer.Exit(1)

    if not files:
        console.print("[yellow]No CKU files found to validate.[/yellow]")
        return

    valid = 0
    invalid = 0
    errors: list[tuple[str, str]] = []

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
            cku = CKU.from_yaml(text)

            # Additional semantic checks
            issues = _check_semantics(cku)
            if issues:
                invalid += 1
                for issue in issues:
                    errors.append((f.name, issue))
                console.print(f"  [yellow]⚠[/yellow] {f.name} — {len(issues)} warning(s)")
            else:
                valid += 1
                console.print(f"  [green]✓[/green] {f.name}")

        except Exception as exc:
            invalid += 1
            errors.append((f.name, str(exc)))
            console.print(f"  [red]✗[/red] {f.name} — {exc}")

    console.print()
    console.print(
        f"[bold]Validated:[/bold] {len(files)} file(s) | "
        f"[green]Valid: {valid}[/green] | "
        f"[{'red' if invalid else 'green'}]Invalid: {invalid}[/]"
    )

    if errors:
        console.print()
        console.print("[bold]Issues:[/bold]")
        for fname, err in errors:
            console.print(f"  {fname}: {err}")
        raise typer.Exit(1)


def _check_semantics(cku: CKU) -> list[str]:
    """Run semantic validation checks beyond schema conformance."""
    from norag.models.cku import CKU

    issues: list[str] = []

    # Check entity ID uniqueness
    entity_ids = [e.id for e in cku.entities]
    if len(entity_ids) != len(set(entity_ids)):
        issues.append("Duplicate entity IDs detected")

    # Check fact ID uniqueness
    fact_ids = [f.id for f in cku.facts]
    if len(fact_ids) != len(set(fact_ids)):
        issues.append("Duplicate fact IDs detected")

    # Check relation targets reference existing entities
    entity_id_set = set(entity_ids)
    for entity in cku.entities:
        for rel in entity.relations:
            if rel.target not in entity_id_set:
                issues.append(f"Entity '{entity.id}' has relation to unknown target '{rel.target}'")

    # Check fact entity references
    for fact in cku.facts:
        for eid in fact.entities:
            if eid not in entity_id_set:
                issues.append(f"Fact '{fact.id}' references unknown entity '{eid}'")

    # Check meta fields
    if not cku.meta.source:
        issues.append("meta.source is empty")
    if not cku.meta.hash:
        issues.append("meta.hash is empty")

    # Check summary
    if not cku.summaries.document:
        issues.append("summaries.document is empty")

    return issues
