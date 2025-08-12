from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st
import yaml
import json


st.title("Metadata Definition Generator")
st.caption("Upload a table file or paste a URL (Excel/CSV/TSV/JSON/YAML) → preview → generate YAML metadata definition.")

uploaded = st.file_uploader(
    "Upload file",
    type=["xlsx", "xls", "csv", "tsv", "txt", "json", "yaml", "yml"],
)
url = st.text_input("Or paste a direct file URL (xlsx/xls/csv/tsv/json/yaml)")
load = st.button("Load")

df: Optional[pd.DataFrame] = None
table_name: str = "table"
source_str = "user_upload"

def _simple_dtype(series: pd.Series) -> str:
    dt = str(series.dtype)
    if dt.startswith("int"):
        return "integer"
    if dt.startswith("float"):
        return "float"
    if dt.startswith("bool"):
        return "boolean"
    try:
        sample = series.dropna().astype(str).head(20)
        parsed = pd.to_datetime(sample, errors="coerce", utc=True)
        if parsed.notna().mean() > 0.6:
            return "date"
    except Exception:
        pass
    return "string"


_ID_PATTERNS: List[tuple[str, str]] = [
    (r"^ENSG\d{6,}$", "Ensembl Gene"),
    (r"^ENST\d{6,}$", "Ensembl Transcript"),
    (r"^ENSP\d{6,}$", "Ensembl Protein"),
    (r"^HGNC:\d+$", "HGNC"),
    (r"^(MONDO|HP|GO|CHEBI):\d+$", "Ontology (MONDO/HPO/GO/CHEBI)"),
    (r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$", "UniProtKB"),
    (r"^[A-NR-Z][0-9][A-Z0-9]{3}[0-9]$", "UniProtKB"),
]


def _detect_id_namespace(values: List[str]) -> Optional[str]:
    for pat, ns in _ID_PATTERNS:
        if any(re.match(pat, v) for v in values if isinstance(v, str)):
            return ns
    if any(re.match(r"^[A-Z0-9-]{2,10}$", v) for v in values if isinstance(v, str)):
        return "HGNC Symbol (heuristic)"
    return None


def _infer_role(col: str) -> Optional[str]:
    c = col.strip().lower()
    if c in {"sample_id", "sample", "barcode"} or "sample" in c:
        return "SAMPLE_ID"
    if c in {"patient_id", "subject"} or "patient" in c:
        return "PATIENT_ID"
    if any(k in c for k in ["gene", "hgnc", "ensembl", "uniprot", "symbol"]):
        return "gene_identifier"
    if any(k in c for k in ["condition", "group", "arm", "phenotype", "status", "treatment"]):
        return "grouping"
    if any(k in c for k in ["pvalue", "padj", "fdr", "log2fc", "stat"]):
        return "statistic"
    if any(k in c for k in ["date", "time"]):
        return "date"
    return None


def _build_json(df: pd.DataFrame, table: str, source: str) -> str:
    cols: List[Dict[str, Any]] = []
    for col in list(df.columns):
        series = df[col]
        dtype = _simple_dtype(series)
        try:
            example = str(series.dropna().iloc[0])
        except Exception:
            example = None
        nonnull_ratio = float(series.notna().mean()) if len(series) else 0.0
        required = nonnull_ratio > 0.95
        sample_vals = series.dropna().astype(str).head(50).tolist()
        id_ns = _detect_id_namespace(sample_vals)
        role = _infer_role(col)
        col_entry: Dict[str, Any] = {
            "name": str(col),
            "dtype": dtype,
            "required": bool(required),
        }
        if role:
            col_entry["role"] = role
        if id_ns:
            col_entry["id_namespace"] = id_ns
        if example is not None:
            col_entry["example"] = example
        cols.append(col_entry)
    out = {
        "source": source,
        "table_name": table,
        "columns": cols,
        "notes": "Edit roles/required/id_namespace as needed.",
        "schema_version": "1.0",
    }
    return json.dumps(out, indent=2, ensure_ascii=False)


def _load_from_bytes(name: str, content: bytes) -> pd.DataFrame:
    nl = name.lower()
    if nl.endswith((".xlsx", ".xls")):
        xls = pd.ExcelFile(io.BytesIO(content))
        sheet = xls.sheet_names[0]
        return pd.read_excel(io.BytesIO(content), sheet_name=sheet)
    if nl.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    if nl.endswith((".tsv", ".txt")):
        return pd.read_csv(io.BytesIO(content), sep="\t")
    if nl.endswith((".json", ".yaml", ".yml")):
        text = content.decode("utf-8", errors="ignore")
        data: Any
        data = yaml.safe_load(text)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return pd.DataFrame(v)
        raise RuntimeError("Could not find a table (array of objects) in JSON/YAML")
    raise RuntimeError("Unsupported file extension")


if load:
    try:
        if uploaded is not None:
            df = _load_from_bytes(uploaded.name, uploaded.read())
            source_str = f"upload:{uploaded.name}"
            table_name = (uploaded.name.rsplit("/", 1)[-1]).split(".")[0]
        elif url:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            filename = url.split("/")[-1] or "download"
            df = _load_from_bytes(filename, r.content)
            source_str = url
            table_name = (filename.split(".")[0])
        else:
            st.info("Upload a file or paste a URL, then click Load.")
    except Exception as e:
        st.error(f"Load failed: {e}")

if df is not None:
    st.subheader("Preview")
    st.dataframe(df.head(50))
    if st.button("Generate metadata definition (JSON)"):
        try:
            js = _build_json(df, table_name, source_str)
            st.subheader("Metadata definition (JSON)")
            st.json(json.loads(js))
        except Exception as e:
            st.error(f"YAML generation failed: {e}")

