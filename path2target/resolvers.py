from __future__ import annotations

import re
from typing import Dict, Optional, List, Tuple

import requests


def _safe_get_json(url: str, *, params: dict | None = None, headers: dict | None = None, timeout: int = 20) -> dict | list | None:
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _dedup_rows(rows: List[dict[str, str]]) -> List[dict[str, str]]:
    seen: set[Tuple[str, str]] = set()
    out: List[dict[str, str]] = []
    for row in rows:
        key = (row.get("Type", ""), row.get("Identifier", ""))
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


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
    """Return cross-IDs (HGNC symbol/ID, Ensembl, Entrez, UniProt, RefSeq) with links.

    Strategy:
    1) MyGene.info for broad coverage (symbol, HGNC, Ensembl, Entrez, UniProt, RefSeq)
    2) If missing, use Ensembl Symbol lookup and Ensembl xrefs by Ensembl Gene ID
    3) If still missing, search HGNC REST and UniProt by gene name
    """
    q = (query or "").strip()
    if not q:
        return []

    rows: List[dict[str, str]] = []
    ensgs: List[str] = []
    symbol: str | None = None

    # 1) MyGene.info
    mg = _safe_get_json(
        "https://mygene.info/v3/query",
        params={
            "q": q,
            "species": "human",
            "fields": "symbol,name,hgnc,entrezgene,ensembl.gene,uniprot.Swiss-Prot,refseq.rna,refseq.protein",
            "size": 1,
        },
    )
    if isinstance(mg, dict):
        hits = mg.get("hits", [])
        if hits:
            hit = hits[0]
            symbol = hit.get("symbol") or symbol
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
            # Ensembl genes (list or dict)
            ens_field = hit.get("ensembl")
            if isinstance(ens_field, dict) and ens_field.get("gene"):
                ensgs.append(ens_field.get("gene"))
            elif isinstance(ens_field, list):
                for item in ens_field:
                    if isinstance(item, dict) and item.get("gene"):
                        ensgs.append(item.get("gene"))
            # Entrez
            entrez = hit.get("entrezgene")
            if entrez:
                rows.append({
                    "Type": "NCBI Gene (Entrez)",
                    "Identifier": str(entrez),
                    "URL": f"https://www.ncbi.nlm.nih.gov/gene/{entrez}",
                })
            # UniProt Swiss-Prot
            usp = hit.get("uniprot", {}).get("Swiss-Prot") if isinstance(hit.get("uniprot"), dict) else None
            usp_list = usp if isinstance(usp, list) else ([usp] if isinstance(usp, str) else [])
            for acc in usp_list:
                rows.append({
                    "Type": "UniProtKB",
                    "Identifier": acc,
                    "URL": f"https://www.uniprot.org/uniprotkb/{acc}",
                })
            # RefSeq
            for kind, vals in ("RefSeq RNA", hit.get("refseq", {}).get("rna")), ("RefSeq Protein", hit.get("refseq", {}).get("protein")):
                if vals:
                    if isinstance(vals, list):
                        for v in vals[:20]:
                            rows.append({
                                "Type": kind,
                                "Identifier": v,
                                "URL": f"https://www.ncbi.nlm.nih.gov/nuccore/{v}" if kind == "RefSeq RNA" else f"https://www.ncbi.nlm.nih.gov/protein/{v}",
                            })
                    elif isinstance(vals, str):
                        rows.append({
                            "Type": kind,
                            "Identifier": vals,
                            "URL": f"https://www.ncbi.nlm.nih.gov/nuccore/{vals}" if kind == "RefSeq RNA" else f"https://www.ncbi.nlm.nih.gov/protein/{vals}",
                        })

    # 2) If no Ensembl gene yet, try Ensembl symbol lookup
    if not ensgs and symbol:
        ens = _safe_get_json(
            f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{symbol}",
            headers={"Content-Type": "application/json"},
        )
        if isinstance(ens, dict) and ens.get("id"):
            ensgs.append(ens.get("id"))

    # If still no Ensembl and input looks like symbol, try symbol directly
    if not ensgs and q and q.isalpha():
        ens = _safe_get_json(
            f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{q}",
            headers={"Content-Type": "application/json"},
        )
        if isinstance(ens, dict) and ens.get("id"):
            ensgs.append(ens.get("id"))

    # Record Ensembl genes
    for ensg in dict.fromkeys(ensgs):
        rows.append({
            "Type": "Ensembl Gene",
            "Identifier": ensg,
            "URL": f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={ensg}",
        })
        # Ensembl xrefs to expand UniProt/HGNC/Entrez/RefSeq
        xrefs = _safe_get_json(
            f"https://rest.ensembl.org/xrefs/id/{ensg}",
            headers={"Content-Type": "application/json"},
        )
        if isinstance(xrefs, list):
            for x in xrefs:
                db = x.get("dbname")
                xid = x.get("primary_id") or x.get("display_id")
                if not xid:
                    continue
                if db == "HGNC":
                    rows.append({
                        "Type": "HGNC ID",
                        "Identifier": xid if xid.startswith("HGNC:") else f"HGNC:{xid}",
                        "URL": f"https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/{xid if xid.startswith('HGNC:') else 'HGNC:'+xid}",
                    })
                elif db in {"UniProtKB/Swiss-Prot", "UniProtKB/TrEMBL"}:
                    rows.append({
                        "Type": "UniProtKB",
                        "Identifier": xid,
                        "URL": f"https://www.uniprot.org/uniprotkb/{xid}",
                    })
                elif db == "EntrezGene":
                    rows.append({
                        "Type": "NCBI Gene (Entrez)",
                        "Identifier": xid,
                        "URL": f"https://www.ncbi.nlm.nih.gov/gene/{xid}",
                    })
                elif db.startswith("RefSeq"):
                    kind = "RefSeq RNA" if "mRNA" in (x.get("description") or "").lower() else "RefSeq"
                    rows.append({
                        "Type": kind,
                        "Identifier": xid,
                        "URL": f"https://www.ncbi.nlm.nih.gov/nuccore/{xid}",
                    })

    # 3) If symbol missing rows, try HGNC REST
    if not symbol and q and q.isalpha():
        hgnc = _safe_get_json(
            f"https://rest.genenames.org/search/symbol/{q}",
            headers={"Accept": "application/json"},
        )
        if isinstance(hgnc, dict):
            docs = (hgnc.get("response") or {}).get("docs", [])
            if docs:
                doc = docs[0]
                symbol = symbol or doc.get("symbol")
                if symbol:
                    rows.append({
                        "Type": "HGNC Symbol",
                        "Identifier": symbol,
                        "URL": f"https://www.genenames.org/tools/search/#!/all?query={symbol}",
                    })
                if doc.get("hgnc_id"):
                    rows.append({
                        "Type": "HGNC ID",
                        "Identifier": doc.get("hgnc_id"),
                        "URL": f"https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/{doc.get('hgnc_id')}",
                    })

    # 4) If no UniProt yet but symbol known, query UniProt by gene name
    have_uniprot = any(r.get("Type") == "UniProtKB" for r in rows)
    if symbol and not have_uniprot:
        uni = _safe_get_json(
            "https://rest.uniprot.org/uniprotkb/search",
            params={"query": f"gene:{symbol} AND organism_id:9606", "format": "json", "size": 5},
        )
        if isinstance(uni, dict):
            for res in uni.get("results", [])[:5]:
                acc = res.get("primaryAccession")
                if acc:
                    rows.append({
                        "Type": "UniProtKB",
                        "Identifier": acc,
                        "URL": f"https://www.uniprot.org/uniprotkb/{acc}",
                    })

    return _dedup_rows(rows)


