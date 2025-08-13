from __future__ import annotations

import re
from typing import Any, Dict, List

import pandas as pd


def infer_schema(df: pd.DataFrame, sample_rows: int = 50) -> Dict[str, Any]:
    """Infer simple schema: types, candidate id/label columns, relation hints."""
    summary: Dict[str, Any] = {"columns": [], "hints": {"id_cols": [], "label_cols": [], "relation_cols": []}}
    head = df.head(sample_rows)
    for col in df.columns:
        series = head[col]
        dtype = str(df[col].dtype)
        n_unique = series.nunique(dropna=True)
        sample_vals = [str(v) for v in series.dropna().astype(str).head(5).tolist()]
        col_info = {"name": col, "dtype": dtype, "n_unique": int(n_unique), "samples": sample_vals}
        summary["columns"].append(col_info)
        lower = col.lower()
        if any(tok in lower for tok in ["id", "identifier", "accession", "iri", "curie"]):
            summary["hints"]["id_cols"].append(col)
        if any(tok in lower for tok in ["name", "label", "title", "description"]):
            summary["hints"]["label_cols"].append(col)
        if any(tok in lower for tok in ["predicate", "relation", "edge", "type"]):
            summary["hints"]["relation_cols"].append(col)

    # Value-based hints
    for col in df.columns:
        series = head[col].astype(str)
        if series.str.match(r"^(ENSG|ENST|ENSP)\d+").any():
            summary.setdefault("entity_suggestions", []).append({"column": col, "entity": "gene/protein"})
        if series.str.match(r"^P\d{4,}").any():
            summary.setdefault("entity_suggestions", []).append({"column": col, "entity": "protein (UniProt)"})
        if series.str.contains(r"MONDO:\d+", regex=True).any():
            summary.setdefault("entity_suggestions", []).append({"column": col, "entity": "disease (MONDO)"})
        if series.str.contains(r"CHEBI:\d+", regex=True).any():
            summary.setdefault("entity_suggestions", []).append({"column": col, "entity": "chemical (ChEBI)"})

    return summary



