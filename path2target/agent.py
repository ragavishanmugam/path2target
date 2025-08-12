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


# ---------------- High-level generator ----------------
def _is_url(text: str) -> bool:
    return text.lower().startswith(("http://", "https://"))


def _yaml_from_yaml_json(text: str) -> str | None:
    try:
        data = yaml.safe_load(text)
        if data is not None:
            return yaml.safe_dump(data, sort_keys=False)
    except Exception:
        pass
    return None


def _infer_from_excel(content: bytes, url: str) -> str:
    import io
    import pandas as pd
    xls = pd.ExcelFile(io.BytesIO(content))
    sheets_summary = []
    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, nrows=50)
            cols = [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]
        except Exception:
            cols = []
        sheets_summary.append({"sheet": sheet, "columns": cols})
    tmpl = {"source": "Excel (inferred)", "url": url, "sheets": sheets_summary}
    return yaml.safe_dump(tmpl, sort_keys=False)


def _infer_from_table(content: bytes, url: str, sep: str) -> str:
    import io
    import pandas as pd
    df = pd.read_csv(io.BytesIO(content), sep=sep, nrows=50)
    cols = [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]
    tmpl = {"source": "Table (inferred)", "url": url, "columns": cols}
    return yaml.safe_dump(tmpl, sort_keys=False)


def generate_metadata_from_input(input_text: str) -> Dict[str, str]:
    """Given a DB name or URL, try to produce a metadata YAML and list resources.

    Returns dict with keys: 'yaml' and optional 'resources_markdown'.
    """
    q = (input_text or "").strip()
    if not q:
        return {"yaml": ""}

    resources = web_search_resources(q, max_results=8) if not _is_url(q) else []

    # If URL: fetch and classify
    if _is_url(q):
        try:
            resp = requests.get(q, timeout=30)
            resp.raise_for_status()
            url_lower = q.lower()
            # Direct YAML/JSON text
            y = _yaml_from_yaml_json(resp.text)
            if y:
                return {"yaml": y}
            # Excel
            if url_lower.endswith((".xlsx", ".xls")):
                return {"yaml": _infer_from_excel(resp.content, q)}
            # CSV/TSV/TXT
            if url_lower.endswith(".csv"):
                return {"yaml": _infer_from_table(resp.content, q, sep=",")}
            if url_lower.endswith((".tsv", ".txt")):
                return {"yaml": _infer_from_table(resp.content, q, sep="\t")}
            # HTML: extract candidate links
            html = resp.text
            links: List[str] = []
            if BeautifulSoup is not None:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    links.append(a.get("href"))
            # Normalize absolute
            from urllib.parse import urljoin
            cand = [urljoin(q, h) for h in links if isinstance(h, str)]
            # Prefer yaml/json then excel/csv
            order = [
                [".yaml", ".yml", ".json"],
                [".xlsx", ".xls"],
                [".csv"],
                [".tsv", ".txt"],
            ]
            for exts in order:
                for u in cand:
                    if any(u.lower().endswith(ext) for ext in exts):
                        try:
                            r2 = requests.get(u, timeout=20)
                            r2.raise_for_status()
                            if any(u.lower().endswith(ext) for ext in [".yaml", ".yml", ".json"]):
                                y2 = _yaml_from_yaml_json(r2.text)
                                if y2:
                                    return {"yaml": y2}
                            if any(u.lower().endswith(ext) for ext in [".xlsx", ".xls"]):
                                return {"yaml": _infer_from_excel(r2.content, u)}
                            if u.lower().endswith(".csv"):
                                return {"yaml": _infer_from_table(r2.content, u, sep=",")}
                            if any(u.lower().endswith(ext) for ext in [".tsv", ".txt"]):
                                return {"yaml": _infer_from_table(r2.content, u, sep="\t")}
                        except Exception:
                            continue
            # Fallback skeleton
            y = synthesize_metadata_definition(q, [])
            return {"yaml": y}
        except Exception:
            pass

    # Name-based flow: use resources and try above for each link
    tried: List[str] = []
    for res in resources:
        u = res.url
        if not _is_url(u) or u in tried:
            continue
        tried.append(u)
        try:
            r = requests.get(u, timeout=20)
            r.raise_for_status()
            y = _yaml_from_yaml_json(r.text)
            if y:
                md = "\n".join([f"- [{h.title}]({h.url}) — {h.snippet}" for h in resources])
                return {"yaml": y, "resources_markdown": md}
            url_lower = u.lower()
            if url_lower.endswith((".xlsx", ".xls")):
                md = "\n".join([f"- [{h.title}]({h.url}) — {h.snippet}" for h in resources])
                return {"yaml": _infer_from_excel(r.content, u), "resources_markdown": md}
            if url_lower.endswith(".csv"):
                md = "\n".join([f"- [{h.title}]({h.url}) — {h.snippet}" for h in resources])
                return {"yaml": _infer_from_table(r.content, u, sep=",") , "resources_markdown": md}
            if url_lower.endswith((".tsv", ".txt")):
                md = "\n".join([f"- [{h.title}]({h.url}) — {h.snippet}" for h in resources])
                return {"yaml": _infer_from_table(r.content, u, sep="\t"), "resources_markdown": md}
        except Exception:
            continue

    # Final fallback: synthesized + resources list
    y = synthesize_metadata_definition(q, resources)
    md = "\n".join([f"- [{h.title}]({h.url}) — {h.snippet}" for h in resources])
    return {"yaml": y, "resources_markdown": md}


