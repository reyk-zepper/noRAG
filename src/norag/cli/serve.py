"""Serve command — starts the noRAG REST API server."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8484, "--port", help="Bind port"),
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory (default: .norag)"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider: claude | ollama"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev mode)"),
) -> None:
    """Start the noRAG REST API server.

    Runs a FastAPI server with endpoints for compile, query, and
    knowledge browsing. API docs available at /docs.
    """
    import uvicorn

    from norag.config import load_config

    config = load_config()
    if store:
        config.store_dir = store
        config.ckus_dir = store / "ckus"
        config.db_path = store / "knowledge.db"
    if provider:
        config.provider = provider
    if model:
        config.model = model

    console.print(f"[bold]noRAG API Server[/bold] — {config.provider}/{config.model}")
    console.print(f"Listening: http://{host}:{port}")
    console.print(f"API Docs:  http://{host}:{port}/docs")
    console.print()

    # Store config in env for the app factory to pick up when using reload
    # For non-reload mode, we pass the app directly
    if reload:
        # In reload mode, uvicorn re-imports the module, so we use the string form
        uvicorn.run(
            "norag.server.app:create_app",
            host=host,
            port=port,
            reload=reload,
            factory=True,
        )
    else:
        from norag.server.app import create_app

        app = create_app(config)
        uvicorn.run(app, host=host, port=port)
