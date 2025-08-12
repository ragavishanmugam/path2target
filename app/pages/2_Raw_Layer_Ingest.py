from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from path2target.ingest import ingest_source
from path2target.schema_infer import infer_schema
import yaml
import requests

st.title("Raw Layer: Ingest + Schema Understanding")

with st.sidebar:
    source = st.selectbox("Source", ["primekg", "csv", "api"], index=0)
    url = st.text_input("URL (for primekg/api)")
    uploaded = st.file_uploader("Upload CSV/TSV")
    use_sample = st.button("Use sample (data/raw/input.csv)")
    run = st.button("Ingest")
    st.divider()
    st.caption("Metadata definition (YAML/JSON)")
    meta_url = st.text_input("Definition URL")
    load_meta_def = st.button("Load definition")

df = None
if use_sample:
    try:
        df = ingest_source("csv", path=Path("data/raw/input.csv"))
        st.success(f"Loaded sample rows: {len(df)}")
    except Exception as e:
        st.error(f"Sample load failed: {e}")
elif run:
    try:
        if uploaded is not None:
            tmp_path = Path("data/_upload.csv")
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(uploaded.getbuffer())
            df = ingest_source("csv", path=tmp_path)
        else:
            df = ingest_source(source, url=url or None)
        st.success(f"Ingested rows: {len(df)}")
    except Exception as e:
        st.error(f"Ingest failed: {e}")

if df is not None:
    st.subheader("Preview")
    st.dataframe(df.head(50))

    st.subheader("Inferred Schema")
    summary = infer_schema(df)
    st.json(summary)

# Metadata definition via URL
if load_meta_def and meta_url:
    try:
        r = requests.get(meta_url, timeout=30)
        r.raise_for_status()
        text = r.text
        # Try YAML first, then JSON
        try:
            data = yaml.safe_load(text)
        except Exception:
            data = None
        if data is None:
            try:
                data = r.json()
            except Exception:
                data = None
        if data is None:
            st.error("Could not parse definition as YAML or JSON.")
        else:
            st.subheader("Loaded metadata definition")
            st.code(yaml.safe_dump(data, sort_keys=False), language="yaml")
    except Exception as e:
        st.error(f"Failed to load definition: {e}")


