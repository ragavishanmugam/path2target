from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from path2target.ingest import ingest_source
from path2target.schema_infer import infer_schema

st.title("Raw Layer: Ingest + Schema Understanding")

with st.sidebar:
    source = st.selectbox("Source", ["primekg", "csv", "api"], index=0)
    url = st.text_input("URL (for primekg/api)")
    uploaded = st.file_uploader("Upload CSV/TSV")
    use_sample = st.button("Use sample (data/raw/input.csv)")
    run = st.button("Ingest")

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


