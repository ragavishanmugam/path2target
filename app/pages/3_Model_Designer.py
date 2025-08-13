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
from path2target.apis import EnsemblAPI, UniProtAPI, ReactomeAPI, safe_api_call

st.title("Intermediate Model Designer")

# ---------------- Existing YAML editor ----------------
if "model_yaml" not in st.session_state:
    st.session_state.model_yaml = default_biolink_skeleton().to_yaml()

# Check if we have a generated model to display
if "generated_model_yaml" in st.session_state:
    st.session_state.model_yaml = st.session_state.generated_model_yaml
    del st.session_state.generated_model_yaml

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

# Biolink Model and BioPAX-inspired properties for each entity type
BIOLINK_BIOPAX_PROPS: Dict[str, List[PropertyDef]] = {
    "_common": [
        PropertyDef("id", True, "string"), 
        PropertyDef("name", False, "string"), 
        PropertyDef("synonyms", False, "array"), 
        PropertyDef("xrefs", False, "array"), 
        PropertyDef("description", False, "string")
    ],
    "gene": [
        PropertyDef("symbol", False, "string"),
        PropertyDef("ncbi_gene_id", False, "string"),
        PropertyDef("ensembl_id", False, "string"),
        PropertyDef("hgnc_id", False, "string"),
        PropertyDef("chromosome", False, "string"),
        PropertyDef("genomic_coordinates", False, "string"),
        PropertyDef("strand", False, "string"),
        PropertyDef("gene_type", False, "string"),  # protein_coding, lncRNA, etc.
        PropertyDef("genetic_map_position", False, "string"),
        PropertyDef("phenotype_associations", False, "array"),
        PropertyDef("expression_sites", False, "array"),
    ],
    "transcript": [
        PropertyDef("ensembl_transcript_id", False, "string"),
        PropertyDef("refseq_id", False, "string"),
        PropertyDef("transcript_type", False, "string"),
        PropertyDef("biotype", False, "string"),
        PropertyDef("length", False, "integer"),
        PropertyDef("coding_sequence_start", False, "integer"),
        PropertyDef("coding_sequence_end", False, "integer"),
        PropertyDef("exon_count", False, "integer"),
        PropertyDef("protein_coding", False, "boolean"),
    ],
    "protein": [
        PropertyDef("uniprot_id", False, "string"),
        PropertyDef("protein_name", False, "string"),
        PropertyDef("molecular_weight", False, "float"),
        PropertyDef("amino_acid_length", False, "integer"),
        PropertyDef("ec_numbers", False, "array"),
        PropertyDef("protein_domains", False, "array"),
        PropertyDef("subcellular_location", False, "array"),
        PropertyDef("protein_family", False, "string"),
        PropertyDef("catalytic_activity", False, "array"),
        PropertyDef("cofactors", False, "array"),
        PropertyDef("post_translational_modifications", False, "array"),
        PropertyDef("protein_interactions", False, "array"),
    ],
    "pathway": [
        PropertyDef("pathway_id", False, "string"),
        PropertyDef("reactome_id", False, "string"),
        PropertyDef("kegg_id", False, "string"),
        PropertyDef("go_id", False, "string"),
        PropertyDef("pathway_type", False, "string"),  # metabolic, signaling, etc.
        PropertyDef("species", False, "string"),
        PropertyDef("pathway_components", False, "array"),
        PropertyDef("evidence_code", False, "string"),
        PropertyDef("confidence_level", False, "string"),
    ],
    "disease": [
        PropertyDef("mondo_id", False, "string"),
        PropertyDef("doid_id", False, "string"),
        PropertyDef("mesh_id", False, "string"),
        PropertyDef("disease_category", False, "string"),
        PropertyDef("inheritance_pattern", False, "string"),
        PropertyDef("age_of_onset", False, "string"),
        PropertyDef("severity", False, "string"),
        PropertyDef("affected_organs", False, "array"),
        PropertyDef("clinical_manifestations", False, "array"),
        PropertyDef("genetic_associations", False, "array"),
    ],
    "drug": [
        PropertyDef("chembl_id", False, "string"),
        PropertyDef("drugbank_id", False, "string"),
        PropertyDef("inchi", False, "string"),
        PropertyDef("smiles", False, "string"),
        PropertyDef("molecular_formula", False, "string"),
        PropertyDef("drug_type", False, "string"),  # small_molecule, antibody, etc.
        PropertyDef("mechanism_of_action", False, "string"),
        PropertyDef("therapeutic_class", False, "string"),
        PropertyDef("indication", False, "array"),
        PropertyDef("contraindications", False, "array"),
        PropertyDef("side_effects", False, "array"),
        PropertyDef("pharmacokinetics", False, "string"),
    ],
    "phenotype": [
        PropertyDef("hpo_id", False, "string"),
        PropertyDef("phenotype_category", False, "string"),
        PropertyDef("severity", False, "string"),
        PropertyDef("frequency", False, "string"),
        PropertyDef("age_of_onset", False, "string"),
        PropertyDef("body_system_affected", False, "array"),
        PropertyDef("clinical_description", False, "string"),
    ],
    "tissue": [
        PropertyDef("uberon_id", False, "string"),
        PropertyDef("bto_id", False, "string"),
        PropertyDef("tissue_type", False, "string"),
        PropertyDef("anatomical_system", False, "string"),
        PropertyDef("development_stage", False, "string"),
        PropertyDef("cell_types", False, "array"),
        PropertyDef("expressed_genes", False, "array"),
    ],
    "cell_line": [
        PropertyDef("cellosaurus_id", False, "string"),
        PropertyDef("atcc_id", False, "string"),
        PropertyDef("cell_type", False, "string"),
        PropertyDef("species", False, "string"),
        PropertyDef("tissue_origin", False, "string"),
        PropertyDef("disease_association", False, "string"),
        PropertyDef("culture_conditions", False, "string"),
        PropertyDef("genetic_modifications", False, "array"),
    ],
    "sample": [
        PropertyDef("sample_type", False, "string"),
        PropertyDef("collection_method", False, "string"),
        PropertyDef("storage_conditions", False, "string"),
        PropertyDef("preservation_method", False, "string"),
        PropertyDef("quality_metrics", False, "array"),
        PropertyDef("batch_id", False, "string"),
        PropertyDef("collection_date", False, "date"),
    ],
}

def _props_for(ent: str) -> List[PropertyDef]:
    """Get entity-specific properties based on Biolink and BioPAX models."""
    common_props = list(BIOLINK_BIOPAX_PROPS["_common"])
    specific_props = list(BIOLINK_BIOPAX_PROPS.get(ent, []))
    return common_props + specific_props

def _suggest_relations(cats: Set[str]) -> List[RelationDef]:
    """Generate comprehensive Biolink/BioPAX-inspired relationships based on entity categories."""
    rels: List[RelationDef] = []
    def has(a: str, b: str) -> bool:
        return a in cats and b in cats
    
    # Central Dogma relationships
    if has("gene", "transcript"):
        rels.append(RelationDef("Gene", "transcribed_to", "Transcript"))
        rels.append(RelationDef("Gene", "has_transcript", "Transcript"))
    if has("transcript", "protein"):
        rels.append(RelationDef("Transcript", "translated_to", "Protein"))
        rels.append(RelationDef("Protein", "encoded_by", "Transcript"))
    if has("gene", "protein"):
        rels.append(RelationDef("Gene", "encodes", "Protein"))
        rels.append(RelationDef("Protein", "encoded_by", "Gene"))
    
    # Pathway relationships
    if has("protein", "pathway"):
        rels.append(RelationDef("Protein", "participates_in", "Pathway"))
        rels.append(RelationDef("Pathway", "has_participant", "Protein"))
    if has("gene", "pathway"):
        rels.append(RelationDef("Gene", "involved_in", "Pathway"))
        rels.append(RelationDef("Pathway", "involves", "Gene"))
    
    # Disease relationships
    if has("gene", "disease"):
        rels.append(RelationDef("Gene", "associated_with", "Disease"))
        rels.append(RelationDef("Gene", "contributes_to", "Disease"))
        rels.append(RelationDef("Disease", "has_genetic_association", "Gene"))
    if has("protein", "disease"):
        rels.append(RelationDef("Protein", "associated_with", "Disease"))
        rels.append(RelationDef("Disease", "involves_protein", "Protein"))
    if has("phenotype", "disease"):
        rels.append(RelationDef("Phenotype", "manifests_in", "Disease"))
        rels.append(RelationDef("Disease", "has_phenotype", "Phenotype"))
    if has("pathway", "disease"):
        rels.append(RelationDef("Pathway", "disrupted_in", "Disease"))
        rels.append(RelationDef("Disease", "disrupts", "Pathway"))
    
    # Drug relationships
    if has("drug", "disease"):
        rels.append(RelationDef("Drug", "treats", "Disease"))
        rels.append(RelationDef("Drug", "indicated_for", "Disease"))
        rels.append(RelationDef("Disease", "treated_by", "Drug"))
    if has("drug", "protein"):
        rels.append(RelationDef("Drug", "targets", "Protein"))
        rels.append(RelationDef("Drug", "binds_to", "Protein"))
        rels.append(RelationDef("Protein", "targeted_by", "Drug"))
    if has("drug", "pathway"):
        rels.append(RelationDef("Drug", "modulates", "Pathway"))
        rels.append(RelationDef("Pathway", "modulated_by", "Drug"))
    if has("drug", "phenotype"):
        rels.append(RelationDef("Drug", "ameliorates", "Phenotype"))
        rels.append(RelationDef("Phenotype", "ameliorated_by", "Drug"))
    
    # Sample and tissue relationships
    if has("sample", "tissue"):
        rels.append(RelationDef("Sample", "derived_from", "Tissue"))
        rels.append(RelationDef("Tissue", "source_of", "Sample"))
    if has("cell_line", "tissue"):
        rels.append(RelationDef("CellLine", "derived_from", "Tissue"))
        rels.append(RelationDef("Tissue", "gives_rise_to", "CellLine"))
    if has("sample", "disease"):
        rels.append(RelationDef("Sample", "has_disease_state", "Disease"))
        rels.append(RelationDef("Disease", "observed_in", "Sample"))
    if has("tissue", "disease"):
        rels.append(RelationDef("Tissue", "affected_by", "Disease"))
        rels.append(RelationDef("Disease", "affects", "Tissue"))
    
    # Expression and localization relationships
    if has("gene", "tissue"):
        rels.append(RelationDef("Gene", "expressed_in", "Tissue"))
        rels.append(RelationDef("Tissue", "expresses", "Gene"))
    if has("protein", "tissue"):
        rels.append(RelationDef("Protein", "expressed_in", "Tissue"))
        rels.append(RelationDef("Tissue", "expresses", "Protein"))
    if has("phenotype", "tissue"):
        rels.append(RelationDef("Phenotype", "manifests_in", "Tissue"))
        rels.append(RelationDef("Tissue", "exhibits", "Phenotype"))
    
    # Protein-protein interactions
    if has("protein", "protein"):
        rels.append(RelationDef("Protein", "interacts_with", "Protein"))
        rels.append(RelationDef("Protein", "binds_to", "Protein"))
    
    # Cell line relationships
    if has("cell_line", "disease"):
        rels.append(RelationDef("CellLine", "model_of", "Disease"))
        rels.append(RelationDef("Disease", "modeled_by", "CellLine"))
    if has("cell_line", "gene"):
        rels.append(RelationDef("CellLine", "expresses", "Gene"))
        rels.append(RelationDef("Gene", "expressed_in", "CellLine"))
    
    return rels

def _discover_related_entities(entities: List[str]) -> Dict[str, List[str]]:
    """Discover related entities using API calls based on entered entities."""
    related = {"suggested_entities": [], "api_discoveries": []}
    
    for entity in entities:
        entity_lower = entity.lower()
        
        # Gene-based discoveries
        if any(keyword in entity_lower for keyword in ["gene", "transcript", "dna"]):
            try:
                # Example: if user enters "BRCA1", suggest related proteins, pathways
                gene_info = safe_api_call(EnsemblAPI.get_gene_info, entity)
                if gene_info:
                    related["api_discoveries"].append(f"Found gene info for {entity}")
                    related["suggested_entities"].extend(["Protein", "Transcript", "Pathway"])
            except:
                pass
        
        # Protein-based discoveries
        if any(keyword in entity_lower for keyword in ["protein", "enzyme"]):
            try:
                proteins = safe_api_call(UniProtAPI.get_proteins_by_gene, entity)
                if proteins:
                    related["api_discoveries"].append(f"Found {len(proteins)} proteins for {entity}")
                    related["suggested_entities"].extend(["Pathway", "Disease", "Drug", "Tissue"])
                    # Get pathways for first protein
                    if proteins:
                        first_protein = proteins[0].get('primaryAccession', '')
                        if first_protein:
                            pathways = safe_api_call(ReactomeAPI.get_pathways_by_protein, first_protein)
                            if pathways:
                                related["api_discoveries"].append(f"Found {len(pathways)} pathways for protein {first_protein}")
            except:
                pass
        
        # Disease-based discoveries
        if any(keyword in entity_lower for keyword in ["disease", "disorder", "syndrome", "cancer"]):
            related["suggested_entities"].extend(["Gene", "Protein", "Phenotype", "Drug", "Sample", "Tissue"])
            related["api_discoveries"].append(f"Disease context detected for {entity} - suggesting genetic and molecular entities")
        
        # Drug-based discoveries
        if any(keyword in entity_lower for keyword in ["drug", "compound", "inhibitor", "agonist", "antagonist"]):
            related["suggested_entities"].extend(["Protein", "Disease", "Pathway", "Phenotype"])
            related["api_discoveries"].append(f"Drug context detected for {entity} - suggesting target and indication entities")
    
    # Add common biomedical entities based on context
    if any(cat in ["gene", "protein", "disease"] for cat in [_canon(e) for e in entities]):
        related["suggested_entities"].extend(["Sample", "Tissue", "CellLine"])
    
    # Remove duplicates and original entities
    related["suggested_entities"] = list(set(related["suggested_entities"]))
    original_canonical = [_canon(e) for e in entities]
    related["suggested_entities"] = [e for e in related["suggested_entities"] 
                                   if _canon(e) not in original_canonical]
    
    return related

entities_text = st.text_input(
    "Key entities (comma-separated)",
    placeholder="Gene, Protein, Disease, Drug, Pathway, Sample, Tissue, Phenotype, Transcript, CellLine",
)

# Show entity-specific property preview
if entities_text:
    preview_entities = [e.strip() for e in entities_text.split(",") if e.strip()]
    if preview_entities:
        st.caption("🔬 **Entity Property Preview (Biolink/BioPAX-based):**")
        
        cols = st.columns(min(len(preview_entities), 3))
        for i, entity in enumerate(preview_entities[:3]):  # Show max 3 previews
            canon_entity = _canon(entity)
            props = _props_for(canon_entity)
            
            with cols[i % 3]:
                st.markdown(f"**{entity}** ({canon_entity})")
                st.write(f"• {len(props)} properties")
                common_count = len(BIOLINK_BIOPAX_PROPS["_common"])
                specific_count = len(props) - common_count
                if specific_count > 0:
                    st.write(f"• {specific_count} domain-specific")
                    # Show first few specific properties
                    specific_props = props[common_count:common_count+3]
                    for prop in specific_props:
                        st.write(f"  - {prop.name} ({prop.datatype})")
                else:
                    st.write("• Standard properties only")

entered: List[str] = [e for e in [s.strip() for s in entities_text.split(",")] if e] if entities_text else []
cats: List[str] = [_canon(e) for e in entered]

if entered:
    # Discover related entities
    with st.expander("🔍 Discover Related Entities", expanded=True):
        st.caption("Based on your entities, we'll discover related biological entities using APIs and knowledge graphs.")
        
        if st.button("Discover Related Entities", key="discover_entities"):
            with st.spinner("Discovering related entities..."):
                discovered = _discover_related_entities(entered)
                
                if discovered["suggested_entities"]:
                    st.success(f"💡 Suggested additional entities: {', '.join(discovered['suggested_entities'])}")
                    
                    # Allow user to select which discovered entities to add
                    selected_additional = st.multiselect(
                        "Select additional entities to include:",
                        options=discovered["suggested_entities"],
                        default=discovered["suggested_entities"][:3],  # Select first 3 by default
                        key="selected_additional_entities"
                    )
                    
                    # Update the entities list
                    if selected_additional:
                        all_entities = entered + selected_additional
                        st.info(f"🎯 Updated entity list: {', '.join(all_entities)}")
                        # Update the text input in session state for next regeneration
                        st.session_state.discovered_entities = all_entities
                
                if discovered["api_discoveries"]:
                    st.info("🔍 API Discovery Results:")
                    for discovery in discovered["api_discoveries"]:
                        st.write(f"• {discovery}")
                else:
                    st.warning("No additional entities discovered. Try more specific biological terms.")

    # Use discovered entities if available
    final_entities = st.session_state.get("discovered_entities", entered)
    final_cats = [_canon(e) for e in final_entities]
    
    # Recommend ontologies (union of defaults for chosen entities)
    recommended: Set[str] = set()
    for c in final_cats:
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
        # Use final entities (including discovered ones)
        working_entities = final_entities
        working_cats = final_cats
        
        # Add classes with properties
        for ent, cat in zip(working_entities, working_cats):
            class_name = ent.strip().title().replace(" ", "")
            props = _props_for(cat)
            # Create richer description based on entity type
            if cat in BIOLINK_BIOPAX_PROPS:
                description = f"Biolink/BioPAX-compliant {cat} entity representing {ent} with domain-specific properties."
            else:
                description = f"Auto-generated class for {ent}"
            model.classes[class_name] = EntityClass(name=class_name, description=description, properties=props)
        
        # Add relations based on categories present
        for r in _suggest_relations(set(working_cats)):
            # Map relation subject/object to entered class names if present; else keep canonical
            subj = next((e.strip().title().replace(" ", "") for e, c in zip(working_entities, working_cats) if c.lower() == r.subject.lower()), r.subject)
            obj = next((e.strip().title().replace(" ", "") for e, c in zip(working_entities, working_cats) if c.lower() == r.object.lower()), r.object)
            model.relations.append(RelationDef(subj, r.predicate, obj))
        
        # Ontologies
        model.ontologies = list(selected_onts)

        # Store the generated model and trigger rerun to update the text area
        st.session_state.generated_model_yaml = model.to_yaml()
        try:
            st.session_state.model_obj = model
            st.success("Model generated and loaded into the editor above.")
            st.rerun()
        except Exception as e:
            st.warning(f"Generated YAML, but failed to load: {e}")

