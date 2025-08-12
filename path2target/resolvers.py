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


