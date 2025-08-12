from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from path2target.ingest import ingest_source
from path2target.schema_infer import infer_schema
import yaml
import requests
import re
import streamlit.components.v1 as components
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

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
    st.caption("Or browse a web page and extract candidate definition links")
    page_url = st.text_input("Web page URL")
    open_page = st.button("Open page below")

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

# Web page browsing + link extraction
if open_page and page_url:
    st.subheader("Web page preview")
    try:
        components.iframe(page_url, height=800)
    except Exception:
        st.info("Embedding blocked by site. Showing extracted links instead.")
    # Fetch and extract candidate links
    try:
        resp = requests.get(page_url, timeout=30)
        resp.raise_for_status()
        html = resp.text
        links: list[str] = []
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                if isinstance(href, str):
                    links.append(href)
        else:
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
        # Normalize to absolute URLs
        from urllib.parse import urljoin
        abs_links = [urljoin(page_url, h) for h in links]
        candidates = [u for u in abs_links if re.search(r"\.(ya?ml|json)(\?|$)", u, re.I)]
        if candidates:
            st.subheader("Detected candidate definition links")
            chosen = st.selectbox("Select a link to load", candidates)
            if st.button("Load selected definition"):
                try:
                    r = requests.get(chosen, timeout=30)
                    r.raise_for_status()
                    text = r.text
                    try:
                        data = yaml.safe_load(text)
                    except Exception:
                        data = r.json()
                    st.subheader("Loaded metadata definition")
                    st.code(yaml.safe_dump(data, sort_keys=False), language="yaml")
                except Exception as e:
                    st.error(f"Failed to load selected link: {e}")
        else:
            st.info("No .yaml/.yml/.json links found on the page.")
    except Exception as e:
        st.error(f"Failed to fetch page: {e}")


