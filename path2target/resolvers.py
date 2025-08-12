from __future__ import annotations

import re
from typing import Dict, Optional

import requests


def resolve_to_ensembl_gene(query: str) -> Optional[Dict[str, str]]:
    """Resolve an input (HGNC symbol/ID, Ensembl ID, NCBI Gene ID, common gene name)
    to an Ensembl gene ID and preferred symbol using public APIs.

    Returns dict with keys: 'ensembl_gene_id', 'symbol', 'name' (when available), or None.
    """
    q = (query or "").strip()
    if not q:
        return None

    # If the input already looks like an Ensembl gene ID, validate via Ensembl lookup
    if re.match(r"^ENSG\d{6,}$", q, flags=re.I):
        try:
            r = requests.get(
                f"https://rest.ensembl.org/lookup/id/{q}",
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            if r.ok:
                data = r.json()
                return {
                    "ensembl_gene_id": data.get("id", q),
                    "symbol": data.get("display_name", ""),
                    "name": data.get("description", ""),
                }
        except Exception:
            pass

    # Try MyGene.info as a general resolver
    try:
        params = {
            "q": q,
            "species": "human",
            "fields": "ensembl.gene,symbol,name,entrezgene,hgnc",
            "size": 1,
        }
        r = requests.get("https://mygene.info/v3/query", params=params, timeout=20)
        r.raise_for_status()
        hits = (r.json() or {}).get("hits", [])
        if hits:
            hit = hits[0]
            symbol = hit.get("symbol", "")
            name = hit.get("name", "")
            ensg = None
            ens_field = hit.get("ensembl")
            if isinstance(ens_field, dict):
                ensg = ens_field.get("gene")
            elif isinstance(ens_field, list) and ens_field:
                # pick first gene id
                for item in ens_field:
                    if isinstance(item, dict) and item.get("gene"):
                        ensg = item.get("gene")
                        break
            if ensg:
                return {"ensembl_gene_id": ensg, "symbol": symbol, "name": name}
    except Exception:
        pass

    # Try Ensembl symbol lookup (HGNC symbol)
    try:
        r = requests.get(
            f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{q}",
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        if r.ok:
            data = r.json()
            return {
                "ensembl_gene_id": data.get("id"),
                "symbol": data.get("display_name", q),
                "name": data.get("description", ""),
            }
    except Exception:
        pass

    # No resolution
    return None


def map_gene_ids(query: str) -> list[dict[str, str]]:
    """Return a list of cross-IDs for a gene query with hyperlinks.

    Uses MyGene.info to fetch Ensembl, HGNC, Entrez, and symbol.
    """
    q = (query or "").strip()
    if not q:
        return []
    try:
        params = {
            "q": q,
            "species": "human",
            "fields": "ensembl.gene,symbol,name,entrezgene,hgnc",
            "size": 1,
        }
        r = requests.get("https://mygene.info/v3/query", params=params, timeout=20)
        r.raise_for_status()
        hits = (r.json() or {}).get("hits", [])
        if not hits:
            return []
        hit = hits[0]
        rows: list[dict[str, str]] = []
        symbol = hit.get("symbol")
        if symbol:
            rows.append({
                "Type": "HGNC Symbol",
                "Identifier": symbol,
                "URL": f"https://www.genenames.org/tools/search/#!/all?query={symbol}",
            })
        hgnc_id = hit.get("hgnc")
        if hgnc_id:
            rows.append({
                "Type": "HGNC ID",
                "Identifier": f"HGNC:{hgnc_id}",
                "URL": f"https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:{hgnc_id}",
            })
        ensembl_field = hit.get("ensembl")
        ensgs: list[str] = []
        if isinstance(ensembl_field, dict) and ensembl_field.get("gene"):
            ensgs = [ensembl_field.get("gene")]
        elif isinstance(ensembl_field, list):
            for item in ensembl_field:
                if isinstance(item, dict) and item.get("gene"):
                    ensgs.append(item.get("gene"))
        for ensg in dict.fromkeys(ensgs):  # de-duplicate, preserve order
            rows.append({
                "Type": "Ensembl Gene",
                "Identifier": ensg,
                "URL": f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={ensg}",
            })
        entrez = hit.get("entrezgene")
        if entrez:
            rows.append({
                "Type": "NCBI Gene (Entrez)",
                "Identifier": str(entrez),
                "URL": f"https://www.ncbi.nlm.nih.gov/gene/{entrez}",
            })
        return rows
    except Exception:
        return []


