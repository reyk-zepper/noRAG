import typer

app = typer.Typer(
    name="norag",
    help="noRAG — Knowledge Compiler. Compile documents into machine-optimized knowledge.",
    no_args_is_help=True,
)

# Import and register commands
from norag.cli.compile import compile_cmd
from norag.cli.query import query_cmd

app.command("compile")(compile_cmd)
app.command("query")(query_cmd)
