from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
import os

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


def _curated_resources(query: str) -> List[DiscoveredResource]:
    q = (query or "").lower()
    curated: Dict[str, List[DiscoveredResource]] = {
        "cbio": [
            DiscoveredResource(
                "cBioPortal Data Loading",
                "https://docs.cbioportal.org/data-loading/",
                "How to prepare, validate and load studies",
            )
        ],
        "geo": [
            DiscoveredResource(
                "GEO Series Matrix help",
                "https://www.ncbi.nlm.nih.gov/geo/info/seriestable.html",
                "GEO processed data table format",
            ),
            DiscoveredResource(
                "GEO RNA-seq template",
                "https://www.ncbi.nlm.nih.gov/geo/info/examples/seq_template.xlsx",
                "Example sequencing submission template",
            ),
        ],
        "uniprot": [
            DiscoveredResource(
                "UniProtKB Help",
                "https://www.uniprot.org/help/entry_format",
                "Entry format and fields",
            )
        ],
        "reactome": [
            DiscoveredResource(
                "Reactome Data Submission",
                "https://reactome.org/submit",
                "Guidelines for submitting pathways",
            )
        ],
        "pdb": [
            DiscoveredResource(
                "RCSB PDB Deposition",
                "https://deposit.wwpdb.org/",
                "wwPDB OneDep deposition system",
            )
        ],
        "arrayexpress": [
            DiscoveredResource(
                "ArrayExpress submission",
                "https://www.ebi.ac.uk/biostudies/arrayexpress/submissions",
                "Submission guide",
            )
        ],
        "sra": [
            DiscoveredResource(
                "SRA Submission Portal",
                "https://www.ncbi.nlm.nih.gov/sra/docs/submit/",
                "Sequence Read Archive submission",
            )
        ],
        "ega": [
            DiscoveredResource(
                "EGA submission",
                "https://ega-archive.org/submission",
                "European Genome-phenome Archive submission",
            )
        ],
        "pride": [
            DiscoveredResource(
                "PRIDE submission",
                "https://www.ebi.ac.uk/pride/markdownpage/submission",
                "Proteomics data submission",
            )
        ],
    }
    for key, items in curated.items():
        if key in q:
            return items
    # default handful
    return curated.get("geo", [])


def web_search_resources(query: str, max_results: int = 8) -> List[DiscoveredResource]:
    # 1) Try DuckDuckGo if available
    if _HAS_DDG:
        hits: List[DiscoveredResource] = []
        with DDGS() as ddgs:  # type: ignore
            for r in ddgs.text(query, max_results=max_results):
                hits.append(
                    DiscoveredResource(r.get("title", ""), r.get("href", ""), r.get("body", ""))
                )
        if hits:
            return hits

    # 2) Try SerpAPI if API key provided (no extra dependency required)
    serp_key = os.environ.get("SERPAPI_KEY") or os.environ.get("SERPAPI_API_KEY")
    if serp_key:
        try:
            resp = requests.get(
                "https://serpapi.com/search.json",
                params={"engine": "google", "q": query, "api_key": serp_key, "num": max_results},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("organic_results") or []
            hits: List[DiscoveredResource] = []
            for r in results[:max_results]:
                hits.append(
                    DiscoveredResource(r.get("title", ""), r.get("link", ""), r.get("snippet", ""))
                )
            if hits:
                return hits
        except Exception:
            pass

    # 3) Fallback curated
    return _curated_resources(query)


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


