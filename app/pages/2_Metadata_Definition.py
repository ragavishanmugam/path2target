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
excel_state_key = "metadata_def_excel"

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


def _summarize_df(df: pd.DataFrame, file_name: str, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for col in list(df.columns):
        s = df[col]
        dtype = _simple_dtype(s)
        try:
            example = str(s.dropna().iloc[0])
        except Exception:
            example = None
        nonnull_ratio = float(s.notna().mean()) if len(s) else 0.0
        required = nonnull_ratio > 0.95
        id_ns = _detect_id_namespace(s.dropna().astype(str).head(50).tolist())
        role = _infer_role(col)
        rows.append({
            "file": file_name,
            "sheet": sheet_name or "-",
            "column": str(col),
            "dtype": dtype,
            "required": bool(required),
            "role": role or "",
            "id_namespace": id_ns or "",
            "example": example or "",
        })
    return rows


def _load_from_bytes(name: str, content: bytes) -> pd.DataFrame:
    nl = name.lower()
    if nl.endswith((".xlsx", ".xls")):
        # For Excel, we don't return a DataFrame here; we stash bytes and sheet names for multi-sheet handling
        xls = pd.ExcelFile(io.BytesIO(content))
        st.session_state[excel_state_key] = {
            "bytes": content,
            "sheets": xls.sheet_names,
            "filename": name,
        }
        # Return an empty frame as placeholder
        return pd.DataFrame()
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

# Excel multi-sheet handling
if excel_state_key in st.session_state:
    ex = st.session_state[excel_state_key]
    sheets = st.multiselect("Select sheets", ex["sheets"], default=ex["sheets"])  # default all
    if not sheets:
        st.info("Pick at least one sheet.")
    all_rows: List[Dict[str, Any]] = []
    for sheet in sheets:
        try:
            edf = pd.read_excel(io.BytesIO(ex["bytes"]), sheet_name=sheet)
        except Exception as e:
            st.error(f"Failed to read sheet '{sheet}': {e}")
            continue
        st.subheader(f"Preview — {sheet}")
        st.dataframe(edf.head(50))
        all_rows.extend(_summarize_df(edf, ex["filename"], sheet))

    if all_rows:
        st.subheader("Consolidated metadata definition (all selected sheets)")
        summary_df = pd.DataFrame(all_rows, columns=[
            "file", "sheet", "column", "dtype", "required", "role", "id_namespace", "example"
        ])
        st.dataframe(summary_df, use_container_width=True)

# Non-Excel single-table handling
elif df is not None:
    st.subheader("Preview")
    st.dataframe(df.head(50))
    # Single-table consolidated summary
    rows = _summarize_df(df, table_name)
    summary_df = pd.DataFrame(rows, columns=[
        "file", "sheet", "column", "dtype", "required", "role", "id_namespace", "example"
    ])
    st.subheader("Metadata definition (table)")
    st.dataframe(summary_df, use_container_width=True)

