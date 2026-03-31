"""Bench command — run noRAG benchmarks."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def bench_cmd(
    dataset: Path = typer.Argument(..., help="Path to benchmark dataset directory"),
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory (default: .norag)"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider: claude | ollama"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    output: Path = typer.Option(None, "--output", "-o", help="Save JSON report to file"),
    no_compile: bool = typer.Option(False, "--no-compile", help="Skip compilation (use existing CKUs)"),
) -> None:
    """Run a benchmark against a dataset.

    The dataset directory must contain:
      - docs/          — documents to compile (.md, .pdf)
      - questions.json — benchmark questions with expected keywords

    Example:
        norag bench benchmarks/sample --provider ollama --model qwen2.5:7b
    """
    from norag.config import load_config
    from norag.bench.dataset import load_dataset
    from norag.bench.runner import BenchRunner
    from norag.bench.report import print_report, save_json_report

    config = load_config()
    if store:
        config.store_dir = store
        config.ckus_dir = store / "ckus"
        config.db_path = store / "knowledge.db"
        config.audit_path = store / "audit.db"
    if provider:
        config.provider = provider
    if model:
        config.model = model

    console.print(f"[bold]noRAG Benchmark[/bold] — {config.provider}/{config.model}")
    console.print(f"Dataset: {dataset}")
    console.print()

    try:
        ds = load_dataset(dataset)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    console.print(f"Documents: {len(ds.doc_files)} | Questions: {len(ds.questions)}")
    console.print()

    runner = BenchRunner(config)
    results = runner.run(ds, force_compile=not no_compile)

    print_report(results)

    if output:
        save_json_report(results, output)
