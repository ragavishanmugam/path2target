from __future__ import annotations

from typing import Dict, List, Set

import streamlit as st

from path2target.model import (
    IntermediateModel,
    EntityClass,
    PropertyDef,
    RelationDef,
    default_biolink_skeleton,
)
from path2target.ols import search_ontology_terms

st.title("Intermediate Model Designer")

# ---------------- Existing YAML editor ----------------
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


# ---------------- Modeling helper (entities → model) ----------------
st.divider()
st.subheader("Modeling helper — from key entities to a logical model")
st.caption("Enter the core entities; we'll propose ontologies, properties, and relationships.")

entities_text = st.text_input(
    "Key entities (comma-separated)",
    placeholder="Gene, Protein, Disease, Drug, Pathway, Sample, Tissue, Phenotype, Transcript, CellLine",
)

def _canon(ent: str) -> str:
    e = ent.strip().lower()
    aliases = {
        "genes": "gene",
        "protein": "protein",
        "proteins": "protein",
        "pathways": "pathway",
        "disease": "disease",
        "diseases": "disease",
        "drug": "drug",
        "drugs": "drug",
        "phenotype": "phenotype",
        "phenotypes": "phenotype",
        "tissue": "tissue",
        "tissues": "tissue",
        "sample": "sample",
        "samples": "sample",
        "transcript": "transcript",
        "transcripts": "transcript",
        "cell line": "cell_line",
        "cellline": "cell_line",
        "cell lines": "cell_line",
    }
    return aliases.get(e, e)

DEFAULT_ONTS: Dict[str, List[str]] = {
    "gene": ["HGNC", "Ensembl", "NCBIGene", "SO"],
    "transcript": ["Ensembl", "RefSeq", "SO"],
    "protein": ["UniProt", "PR"],
    "pathway": ["Reactome", "KEGG", "GO"],
    "disease": ["MONDO", "DOID", "MeSH"],
    "phenotype": ["HPO"],
    "drug": ["ChEMBL", "DrugBank", "RxNorm"],
    "tissue": ["UBERON", "BTO"],
    "cell_line": ["CLO", "Cellosaurus"],
    "sample": ["EFO", "OBI"],
}

DEFAULT_PROPS: Dict[str, List[PropertyDef]] = {
    "_common": [PropertyDef("id", True), PropertyDef("name"), PropertyDef("synonyms"), PropertyDef("xrefs"), PropertyDef("description")],
}

def _props_for(ent: str) -> List[PropertyDef]:
    return list(DEFAULT_PROPS["_common"])

def _suggest_relations(cats: Set[str]) -> List[RelationDef]:
    rels: List[RelationDef] = []
    def has(a: str, b: str) -> bool:
        return a in cats and b in cats
    if has("gene", "transcript"):
        rels.append(RelationDef("Gene", "transcribes_to", "Transcript"))
    if has("transcript", "protein"):
        rels.append(RelationDef("Transcript", "translates_to", "Protein"))
    if has("protein", "pathway"):
        rels.append(RelationDef("Protein", "participates_in", "Pathway"))
    if has("gene", "pathway"):
        rels.append(RelationDef("Gene", "involved_in", "Pathway"))
    if has("gene", "disease"):
        rels.append(RelationDef("Gene", "associated_with", "Disease"))
    if has("drug", "disease"):
        rels.append(RelationDef("Drug", "treats", "Disease"))
    if has("drug", "protein"):
        rels.append(RelationDef("Drug", "targets", "Protein"))
    if has("sample", "tissue"):
        rels.append(RelationDef("Sample", "derived_from", "Tissue"))
    if has("phenotype", "disease"):
        rels.append(RelationDef("Phenotype", "characterizes", "Disease"))
    if has("cell_line", "tissue"):
        rels.append(RelationDef("CellLine", "derived_from", "Tissue"))
    if has("sample", "disease"):
        rels.append(RelationDef("Sample", "has_disease", "Disease"))
    return rels

entered: List[str] = [e for e in [s.strip() for s in entities_text.split(",")] if e] if entities_text else []
cats: List[str] = [_canon(e) for e in entered]

if entered:
    # Recommend ontologies (union of defaults for chosen entities)
    recommended: Set[str] = set()
    for c in cats:
        for o in DEFAULT_ONTS.get(c, []):
            recommended.add(o)
    selected_onts = st.multiselect(
        "Recommended ontologies (you can add/remove)",
        options=sorted(list(recommended)),
        default=sorted(list(recommended)),
        key="model_helper_onts",
    )

    with st.expander("Optional: Search OLS to discover terms", expanded=False):
        q = st.text_input("Search terms (OLS)", value=(entered[0] if entered else ""), key="ols_q")
        if q:
            try:
                hits = search_ontology_terms(q, size=10)
                if hits:
                    st.table([
                        {
                            "label": h.get("label"),
                            "ontology": h.get("ontology_name"),
                            "iri": h.get("iri"),
                        }
                        for h in hits
                    ])
                else:
                    st.info("No OLS hits.")
            except Exception as e:
                st.warning(f"OLS search failed: {e}")

    if st.button("Generate model from entities"):
        model = IntermediateModel()
        # Add classes with properties
        for ent, cat in zip(entered, cats):
            class_name = ent.strip().title().replace(" ", "")
            props = _props_for(cat)
            model.classes[class_name] = EntityClass(name=class_name, description=f"Auto-generated class for {ent}", properties=props)
        # Add relations based on categories present
        for r in _suggest_relations(set(cats)):
            # Map relation subject/object to entered class names if present; else keep canonical
            subj = next((e.strip().title().replace(" ", "") for e, c in zip(entered, cats) if c.lower() == r.subject.lower()), r.subject)
            obj = next((e.strip().title().replace(" ", "") for e, c in zip(entered, cats) if c.lower() == r.object.lower()), r.object)
            model.relations.append(RelationDef(subj, r.predicate, obj))
        # Ontologies
        model.ontologies = list(selected_onts)

        st.session_state.model_yaml = model.to_yaml()
        try:
            st.session_state.model_obj = model
            st.success("Model generated and loaded into the editor above.")
        except Exception as e:
            st.warning(f"Generated YAML, but failed to load: {e}")

