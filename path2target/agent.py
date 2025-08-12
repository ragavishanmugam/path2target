from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from duckduckgo_search import DDGS  # type: ignore
import requests
from bs4 import BeautifulSoup  # type: ignore
from readability import Document  # type: ignore
import yaml


@dataclass
class DiscoveredResource:
    title: str
    url: str
    snippet: str


def web_search_resources(query: str, max_results: int = 8) -> List[DiscoveredResource]:
    hits: List[DiscoveredResource] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            hits.append(DiscoveredResource(r.get("title", ""), r.get("href", ""), r.get("body", "")))
    return hits


def fetch_and_extract(url: str) -> Dict[str, str]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    html = resp.text
    doc = Document(html)
    content_html = doc.summary()
    soup = BeautifulSoup(content_html, "html.parser")
    text = soup.get_text("\n")
    return {"title": doc.short_title(), "text": text}


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


