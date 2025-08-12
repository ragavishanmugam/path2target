from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from .ingest import ingest_source
from .transform import run_transformations

app = typer.Typer(help="path2target CLI")


@app.command()
def ingest(
    source: str = typer.Option(..., help="Source key: primekg, csv, api"),
    url: Optional[str] = typer.Option(None, help="HTTP/FTP URL to fetch"),
    path: Optional[Path] = typer.Option(None, help="Local path to file"),
    out: Path = typer.Option(Path("data/raw/input.csv"), help="Output path for raw data"),
):
    """Ingest data from a source into a local raw file."""
    out.parent.mkdir(parents=True, exist_ok=True)
    df = ingest_source(source=source, url=url, path=path)
    df.to_csv(out, index=False)
    typer.echo(f"Wrote raw file to {out}")


@app.command()
def transform(
    config: Path = typer.Option(..., help="YAML mapping config"),
    outdir: Path = typer.Option(Path("outputs"), help="Output directory"),
):
    """Run transformations and export RDF/JSON-LD/TSV."""
    outdir.mkdir(parents=True, exist_ok=True)
    result = run_transformations(config=config, outdir=outdir)
    (outdir / "provenance.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    typer.echo(f"Transformations complete. Outputs in {outdir}")


if __name__ == "__main__":
    app()


