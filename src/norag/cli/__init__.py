from typing import Optional

import typer

from norag import __version__


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"noRAG {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="norag",
    help="noRAG — Knowledge Compiler. Compile documents into machine-optimized knowledge.",
    no_args_is_help=True,
)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


# Import and register commands
from norag.cli.compile import compile_cmd
from norag.cli.query import query_cmd
from norag.cli.watch import watch_cmd
from norag.cli.serve import serve_cmd
from norag.cli.audit import audit_cmd
from norag.cli.bench import bench_cmd
from norag.cli.info import info_cmd
from norag.cli.validate import validate_cmd

app.command("compile")(compile_cmd)
app.command("query")(query_cmd)
app.command("watch")(watch_cmd)
app.command("serve")(serve_cmd)
app.command("audit")(audit_cmd)
app.command("bench")(bench_cmd)
app.command("info")(info_cmd)
app.command("validate")(validate_cmd)
