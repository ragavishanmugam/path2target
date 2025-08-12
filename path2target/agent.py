from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

try:  # Optional deps for agentic mode
    from duckduckgo_search import DDGS  # type: ignore
    _HAS_DDG = True
except Exception:  # pragma: no cover
    DDGS = None  # type: ignore
    _HAS_DDG = False

import requests
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore
try:
    from readability import Document  # type: ignore
    _HAS_READABILITY = True
except Exception:  # pragma: no cover
    Document = None  # type: ignore
    _HAS_READABILITY = False
import yaml


@dataclass
class DiscoveredResource:
    title: str
    url: str
    snippet: str


def web_search_resources(query: str, max_results: int = 8) -> List[DiscoveredResource]:
    if not _HAS_DDG:
        return []
    hits: List[DiscoveredResource] = []
    with DDGS() as ddgs:  # type: ignore
        for r in ddgs.text(query, max_results=max_results):
            hits.append(DiscoveredResource(r.get("title", ""), r.get("href", ""), r.get("body", "")))
    return hits


def fetch_and_extract(url: str) -> Dict[str, str]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    html = resp.text
    title = url
    text = html
    if _HAS_READABILITY and Document is not None:
        try:
            doc = Document(html)
            title = doc.short_title()
            content_html = doc.summary()
            if BeautifulSoup is not None:
                soup = BeautifulSoup(content_html, "html.parser")
                text = soup.get_text("\n")
        except Exception:
            pass
    return {"title": title, "text": text}


def synthesize_metadata_definition(db_name: str, resources: List[DiscoveredResource]) -> str:
    """Produce a best-effort YAML definition from discovered resources.

    This is heuristic, meant to give the user a starting point.
    """
    tmpl = {
        "source": db_name,
        "description": f"Auto-discovered submission/ingestion requirements for {db_name}",
        "resources": [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in resources],
        "files": [
            {"name": "<file_1>", "required": False, "format": "<format>", "columns": []},
        ],
        "notes": "Review linked resources and refine the template with exact fields/formats.",
    }
    return yaml.safe_dump(tmpl, sort_keys=False)


