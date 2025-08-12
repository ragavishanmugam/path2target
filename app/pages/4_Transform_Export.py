from __future__ import annotations

from pathlib import Path

import streamlit as st

from path2target.transform import run_transformations

st.title("Transformation & Output")

st.markdown("Provide a minimal YAML mapping and export directory to generate RDF/JSON-LD/TSV.")

default_cfg = """
dataset:
  path: data/raw/input.csv
mapping:
  entity: Gene
  id: id
  label: name
  base_iri: http://example.org/gene/
  type_iri: https://w3id.org/biolink/vocab/Gene
"""

cfg_text = st.text_area("Mapping config (YAML)", value=default_cfg, height=240)
outdir = Path(st.text_input("Output directory", value="outputs"))

if st.button("Run transformations"):
    try:
        outdir.mkdir(parents=True, exist_ok=True)
        cfg_path = outdir / "mapping.yaml"
        cfg_path.write_text(cfg_text, encoding="utf-8")
        result = run_transformations(config=cfg_path, outdir=outdir)
        st.success(f"Done. Triples: {result['num_triples']}, rows: {result['num_rows']}")
        st.write("Downloads:")
        st.download_button("export.ttl", data=(outdir/"export.ttl").read_bytes(), file_name="export.ttl")
        st.download_button("export.jsonld", data=(outdir/"export.jsonld").read_bytes(), file_name="export.jsonld")
        st.download_button("export.tsv", data=(outdir/"export.tsv").read_bytes(), file_name="export.tsv")
    except Exception as e:
        st.error(f"Transform failed: {e}")


