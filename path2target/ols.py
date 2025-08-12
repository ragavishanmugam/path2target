from __future__ import annotations

from typing import Dict, List

import requests

OLS_BASE = "https://www.ebi.ac.uk/ols4/api"


def search_ontology_terms(query: str, ontology: str | None = None, size: int = 20) -> List[Dict]:
    params = {"q": query, "size": size}
    if ontology:
        params["ontology"] = ontology
    r = requests.get(f"{OLS_BASE}/search", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("response", {}).get("docs", [])


def get_term(iri: str) -> Dict:
    r = requests.get(f"{OLS_BASE}/terms", params={"iri": iri}, timeout=30)
    r.raise_for_status()
    return r.json()


