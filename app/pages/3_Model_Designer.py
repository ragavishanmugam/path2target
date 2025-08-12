from __future__ import annotations

import streamlit as st

from path2target.model import (
    IntermediateModel,
    EntityClass,
    PropertyDef,
    RelationDef,
    default_biolink_skeleton,
)

st.title("Intermediate Model Designer")

if "model_yaml" not in st.session_state:
    st.session_state.model_yaml = default_biolink_skeleton().to_yaml()

st.text_area("Model (YAML)", key="model_yaml", height=400)

if st.button("Validate & Load"):
    try:
        model = IntermediateModel.from_yaml(st.session_state.model_yaml)
        st.success(f"Loaded model with {len(model.classes)} classes and {len(model.relations)} relations.")
        st.session_state.model_obj = model
    except Exception as e:
        st.error(f"Invalid YAML: {e}")

if "model_obj" in st.session_state:
    model = st.session_state.model_obj
    st.subheader("Classes")
    for name, cls in model.classes.items():
        with st.expander(name, expanded=False):
            st.write(cls.description)
            st.table([{**p.__dict__} for p in cls.properties])


