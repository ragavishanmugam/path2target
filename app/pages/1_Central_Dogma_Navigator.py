from __future__ import annotations

import streamlit as st

st.title("Central Dogma Navigator")
st.caption("Drag data sources onto lanes to indicate contribution")

lanes = ["DNA", "RNA", "Protein", "Pathways"]
cols = st.columns(len(lanes))
for c, lane in zip(cols, lanes):
    with c:
        st.subheader(lane)
        st.container(height=300, border=True)

st.divider()
st.subheader("Sources")
st.write("Ensembl (Genes/Transcripts), UniProt (Proteins), Reactome (Pathways)")
st.info("Drag-and-drop mockup: future enhancement will enable interactive canvas.")


