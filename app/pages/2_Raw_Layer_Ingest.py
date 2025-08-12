from __future__ import annotations
import streamlit as st
from path2target.metadata_defs import get_metadata_definition

st.title("Metadata Definition Generator")
st.caption("Input a database name and get a metadata definition template.")

db = st.text_input("Database name", placeholder="e.g., cBioPortal, GEO (Series Matrix), PandaOmics")
if st.button("Generate definition") and db:
    key = db.strip().lower()
    tmpl = ""
    if "cbio" in key:
        tmpl = get_metadata_definition("cBioPortal")
    elif "geo" in key:
        tmpl = get_metadata_definition("GEO (Series Matrix)")
    elif "panda" in key:
        tmpl = get_metadata_definition("PandaOmics (stub)")
    if tmpl:
        st.subheader("Metadata definition")
        st.code(tmpl, language="yaml")
    else:
        st.info("Unknown database. Try 'cBioPortal', 'GEO (Series Matrix)', or 'PandaOmics'.")

# Legacy implementation commented below to prevent parse errors during reset
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from path2target.ingest import ingest_source
from path2target.schema_infer import infer_schema
from path2target.metadata_defs import get_metadata_definition
try:
    from path2target.agent import generate_metadata_from_input  # type: ignore
    _GEN_AVAILABLE = True
except Exception:  # pragma: no cover
    _GEN_AVAILABLE = False
import yaml
import requests
import re
import streamlit.components.v1 as components
try:
    from path2target.agent import web_search_resources, synthesize_metadata_definition  # type: ignore
    _AGENT_AVAILABLE = True
except Exception:
    _AGENT_AVAILABLE = False
try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

st.title("Metadata Definition Generator")
st.caption("Input a database name; get a metadata definition template.")
db_name = st.text_input("Database name", placeholder="e.g., cBioPortal, GEO (Series Matrix), PandaOmics")
go = st.button("Generate definition")
if go and db_name:
    name_lower = db_name.strip().lower()
    if "cbio" in name_lower:
        tmpl = get_metadata_definition("cBioPortal")
    elif "geo" in name_lower:
        tmpl = get_metadata_definition("GEO (Series Matrix)")
    elif "panda" in name_lower:
        tmpl = get_metadata_definition("PandaOmics (stub)")
    else:
        tmpl = ""
        st.info("Unknown database. Try 'cBioPortal', 'GEO (Series Matrix)', or 'PandaOmics'.")
    if tmpl:
        st.subheader("Metadata definition")
        st.code(tmpl, language="yaml")
st.stop()
    if _AGENT_AVAILABLE:
        st.caption("Or ask the agent to discover submission guidelines")
        agent_query = st.text_input("Agent query (e.g., 'PandaOmics submission guidelines')")
        run_agent = st.button("Search & synthesize")
    else:
        st.caption("Agent search (DuckDuckGo + readability) will appear after the cloud rebuild picks up requirements.")

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
            # Try inferring from file types (xlsx/csv/tsv)
            url_lower = meta_url.lower()
            if any(url_lower.endswith(ext) for ext in [".xlsx", ".xls"]):
                import io
                import pandas as pd
                content = r.content
                try:
                    xls = pd.ExcelFile(io.BytesIO(content))
                    sheets_summary = []
                    for sheet in xls.sheet_names:
                        try:
                            df = pd.read_excel(xls, sheet_name=sheet, nrows=50)
                            cols = []
                            for col in df.columns.tolist():
                                series = df[col]
                                dtype = str(series.dtype)
                                cols.append({"name": str(col), "dtype": dtype})
                            sheets_summary.append({"sheet": sheet, "columns": cols})
                        except Exception:
                            sheets_summary.append({"sheet": sheet, "columns": []})
                    tmpl = {
                        "source": "Excel (inferred)",
                        "url": meta_url,
                        "sheets": sheets_summary,
                    }
                    st.subheader("Loaded metadata definition (inferred from Excel)")
                    st.code(yaml.safe_dump(tmpl, sort_keys=False), language="yaml")
                    st.stop()
                except Exception as e:
                    st.error(f"Failed to parse Excel: {e}")
            elif any(url_lower.endswith(ext) for ext in [".csv", ".tsv", ".txt"]):
                import io
                import pandas as pd
                sep = "," if url_lower.endswith(".csv") else "\t"
                try:
                    df = pd.read_csv(io.BytesIO(r.content), sep=sep, nrows=50)
                    cols = []
                    for col in df.columns.tolist():
                        dtype = str(df[col].dtype)
                        cols.append({"name": str(col), "dtype": dtype})
                    tmpl = {"source": "Table (inferred)", "url": meta_url, "columns": cols}
                    st.subheader("Loaded metadata definition (inferred from table)")
                    st.code(yaml.safe_dump(tmpl, sort_keys=False), language="yaml")
                    st.stop()
                except Exception as e:
                    st.error(f"Failed to parse table: {e}")
            # Recognize known documentation pages and synthesize definition
            if "docs.cbioportal.org/data-loading" in meta_url:
                st.subheader("Loaded metadata definition (cBioPortal)")
                tmpl = get_metadata_definition("cBioPortal")
                st.code(tmpl, language="yaml")
            else:
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
            # Offer synthesized template for recognized docs
            if "docs.cbioportal.org/data-loading" in page_url:
                if st.button("Generate cBioPortal definition from docs"):
                    tmpl = get_metadata_definition("cBioPortal")
                    st.subheader("Generated metadata definition (cBioPortal)")
                    st.code(tmpl, language="yaml")
    except Exception as e:
        st.error(f"Failed to fetch page: {e}")

if auto_go and auto_input:
    with st.spinner("Discovering and generating definition..."):
        if _GEN_AVAILABLE:
            out = generate_metadata_from_input(auto_input)  # type: ignore
            yaml_text = out.get("yaml", "")
            refs = out.get("resources_markdown")
            if refs:
                st.subheader("Discovered resources")
                st.markdown(refs)
            if yaml_text:
                st.subheader("Generated metadata definition")
                st.code(yaml_text, language="yaml")
            else:
                st.info("No definition could be generated. Try a different query or paste a specific URL.")
        else:
            st.info("Generator not yet available. Please click Rerun after the cloud rebuild finishes, or paste a direct definition URL above.")

# Agentic discovery
if _AGENT_AVAILABLE and 'run_agent' in locals() and run_agent and agent_query:
    st.subheader("Agent: discovered resources")
    hits = web_search_resources(agent_query, max_results=8)
    if hits:
        for h in hits:
            st.markdown(f"- [{h.title}]({h.url}) — {h.snippet}")
        # Synthesize a starter YAML
        yaml_text = synthesize_metadata_definition(agent_query, hits)
        st.subheader("Agent: synthesized metadata definition (starter)")
        st.code(yaml_text, language="yaml")
    else:
        st.info("No resources found. Refine your query.")


