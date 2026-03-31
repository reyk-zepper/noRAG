"""Benchmark report — Rich table and JSON output."""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from norag.bench.metrics import BenchResults

console = Console()


def print_report(results: BenchResults) -> None:
    """Print a rich benchmark report to the console."""
    # Summary panel
    summary = (
        f"Dataset: [bold]{results.dataset_name}[/bold]\n"
        f"Documents: {results.compile_doc_count} | "
        f"Questions: {results.total_questions}\n"
        f"Compile Time: {results.compile_time_s:.1f}s\n"
        f"Avg Keyword Score: [{'green' if results.avg_keyword_score >= 0.7 else 'yellow' if results.avg_keyword_score >= 0.4 else 'red'}]"
        f"{results.avg_keyword_score:.1%}[/]\n"
        f"Avg Latency: {results.avg_latency_ms:.0f}ms\n"
        f"Avg Tokens: {results.avg_tokens:.0f}"
    )
    console.print(Panel(summary, title="noRAG Benchmark Results", border_style="blue"))

    # Category scores
    cat_scores = results.category_scores
    if cat_scores:
        cat_table = Table(title="Scores by Category")
        cat_table.add_column("Category", style="bold")
        cat_table.add_column("Score", justify="right")
        cat_table.add_column("Questions", justify="right")

        cat_counts: dict[str, int] = {}
        for r in results.question_results:
            cat_counts[r.category] = cat_counts.get(r.category, 0) + 1

        for cat, score in sorted(cat_scores.items()):
            color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
            cat_table.add_row(
                cat,
                f"[{color}]{score:.1%}[/]",
                str(cat_counts.get(cat, 0)),
            )
        console.print(cat_table)

    # Per-question details
    q_table = Table(title="Per-Question Results")
    q_table.add_column("ID", width=6)
    q_table.add_column("Category", width=16)
    q_table.add_column("Score", justify="right", width=8)
    q_table.add_column("Latency", justify="right", width=10)
    q_table.add_column("Tokens", justify="right", width=8)
    q_table.add_column("Keywords", width=30)

    for r in results.question_results:
        color = "green" if r.keyword_score >= 0.7 else "yellow" if r.keyword_score >= 0.4 else "red"
        matched_str = f"{len(r.matched_keywords)}/{len(r.expected_keywords)}"
        q_table.add_row(
            r.question_id,
            r.category,
            f"[{color}]{r.keyword_score:.0%}[/]",
            f"{r.latency_ms:.0f}ms",
            str(r.token_estimate),
            matched_str,
        )

    console.print(q_table)


def save_json_report(results: BenchResults, output_path: Path) -> None:
    """Save benchmark results as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    console.print(f"[dim]Report saved to {output_path}[/dim]")
