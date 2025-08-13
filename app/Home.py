from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="path2target", layout="wide")
st.title("path2target")
st.markdown("Automated transformation engine for biomedical KGs.")

st.page_link("pages/1_Central_Dogma_Navigator.py", label="Central Dogma Navigator", icon="🧬")
st.page_link("pages/2_Raw_Layer_Ingest.py", label="Raw Layer (Ingest)", icon="📥")
st.page_link("pages/3_Model_Designer.py", label="Intermediate Model Designer", icon="🧩")
st.page_link("pages/4_Transform_Export.py", label="Transform & Export", icon="📤")



