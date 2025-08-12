from __future__ import annotations

from pathlib import Path
from typing import Optional

import io
import requests
import pandas as pd


def ingest_source(source: str, url: Optional[str] = None, path: Optional[Path] = None) -> pd.DataFrame:
    """Ingest a source into a DataFrame.

    - source = primekg: expects a CSV with columns like subject, predicate, object
    - source = csv: load from local path
    - source = api: GET from URL that returns CSV/TSV
    """
    source = source.lower()
    if source == "primekg":
        if url:
            return _read_remote_table(url)
        if path:
            return _read_table(path)
        raise ValueError("primekg requires --url or --path")
    if source == "csv":
        if path:
            return _read_table(path)
        raise ValueError("csv requires --path")
    if source == "api":
        if url:
            return _read_remote_table(url)
        raise ValueError("api requires --url")
    raise ValueError(f"Unknown source: {source}")


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".csv"}:
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


def _read_remote_table(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    content = r.content
    # Try csv, then tsv
    try:
        return pd.read_csv(io.BytesIO(content))
    except Exception:
        return pd.read_csv(io.BytesIO(content), sep="\t")


