import typer

app = typer.Typer(
    name="norag",
    help="noRAG — Knowledge Compiler. Compile documents into machine-optimized knowledge.",
    no_args_is_help=True,
)

# Import and register commands
from norag.cli.compile import compile_cmd
from norag.cli.query import query_cmd
from norag.cli.watch import watch_cmd
from norag.cli.serve import serve_cmd
from norag.cli.audit import audit_cmd
from norag.cli.bench import bench_cmd

app.command("compile")(compile_cmd)
app.command("query")(query_cmd)
app.command("watch")(watch_cmd)
app.command("serve")(serve_cmd)
app.command("audit")(audit_cmd)
app.command("bench")(bench_cmd)
