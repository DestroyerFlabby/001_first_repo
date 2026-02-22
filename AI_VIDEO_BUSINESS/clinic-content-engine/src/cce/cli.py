from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from cce.export import run_export
from cce.generate import run_generate
from cce.ingest import run_ingest
from cce.plan import run_plan
from cce.review import run_review

app = typer.Typer(help="Clinic Content Engine CLI")
console = Console()


def _validate_client_path(client: str) -> Path:
    client_path = Path(client)
    if not client_path.exists() or not client_path.is_dir():
        raise typer.BadParameter(f"Client directory not found: {client_path}")
    return client_path


@app.command("ingest")
def ingest(client: str = typer.Option(..., help="Path to client folder, e.g. clients/ammc")) -> None:
    """Ingest source documents into kb chunks."""
    client_path = _validate_client_path(client)
    run_ingest(client_path, console)


@app.command("plan")
def plan(
    client: str = typer.Option(..., help="Path to client folder"),
    month: str = typer.Option(..., help="Month in YYYY-MM format"),
) -> None:
    """Create monthly content plan."""
    client_path = _validate_client_path(client)
    run_plan(client_path, month, console)


@app.command("generate")
def generate(
    client: str = typer.Option(..., help="Path to client folder"),
    month: str = typer.Option(..., help="Month in YYYY-MM format"),
) -> None:
    """Generate monthly drafts."""
    client_path = _validate_client_path(client)
    run_generate(client_path, month, console)


@app.command("review")
def review(
    client: str = typer.Option(..., help="Path to client folder"),
    month: str = typer.Option(..., help="Month in YYYY-MM format"),
) -> None:
    """Review and fix drafts against guardrails."""
    client_path = _validate_client_path(client)
    run_review(client_path, month, console)


@app.command("export")
def export(
    client: str = typer.Option(..., help="Path to client folder"),
    month: str = typer.Option(..., help="Month in YYYY-MM format"),
) -> None:
    """Export deliverables and audit log."""
    client_path = _validate_client_path(client)
    run_export(client_path, month, console)


if __name__ == "__main__":
    app()
