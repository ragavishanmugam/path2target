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

st.set_page_config(page_title="Data Model Designer", page_icon="🏗️", layout="wide")

# Header with professional styling
st.markdown("""
<div style="background: linear-gradient(90deg, #1f4e79 0%, #2e6da4 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
    <h1 style="color: white; margin: 0; font-size: 2.5rem; font-weight: 600;">🏗️ Biomedical Data Model Designer</h1>
    <p style="color: #e8f4fd; margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
        Design comprehensive data models for pharmaceutical and biomedical data architecture
    </p>
</div>
""", unsafe_allow_html=True)

# Professional info cards
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #28a745;">
        <h4 style="color: #28a745; margin: 0;">📋 Comprehensive Standards</h4>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">Biolink, BioPAX, GO, OMOP, SO, EFO, OBI, CDISC, NCIT integration</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #007bff;">
        <h4 style="color: #007bff; margin: 0;">🔗 Rich Relationships</h4>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">200+ genomic, clinical & trial relationships</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #ffc107;">
        <h4 style="color: #e09900; margin: 0;">🔍 Smart Discovery</h4>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">API-driven entity & relationship discovery</p>
    </div>
    """, unsafe_allow_html=True)

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
        # Extended ontology entities
        "variant": "variant",
        "variants": "variant",
        "snp": "variant",
        "snps": "variant",
        "mutation": "variant",
        "mutations": "variant",
        "allele": "variant",
        "alleles": "variant",
        "genomic_variant": "variant",
        "sequence_variant": "variant",
        "molecular_function": "molecular_function",
        "biological_process": "biological_process",
        "cellular_component": "cellular_component",
        "observation": "observation",
        "observations": "observation",
        "measurement": "measurement",
        "measurements": "measurement",
        "procedure": "procedure",
        "procedures": "procedure",
        "condition": "condition",
        "conditions": "condition",
        "visit": "visit",
        "visits": "visit",
        "cohort": "cohort",
        "cohorts": "cohort",
        "experimental_factor": "experimental_factor",
        "assay": "assay",
        "assays": "assay",
        "sequence_feature": "sequence_feature",
        "sequence_features": "sequence_feature",
    }
    return aliases.get(e, e)

DEFAULT_ONTS: Dict[str, List[str]] = {
    "gene": ["HGNC", "Ensembl", "NCBIGene", "SO"],
    "transcript": ["Ensembl", "RefSeq", "SO"],
    "protein": ["UniProt", "PR", "GO"],
    "pathway": ["Reactome", "KEGG", "GO"],
    "disease": ["MONDO", "DOID", "MeSH", "OMOP"],
    "phenotype": ["HPO", "OMOP"],
    "drug": ["ChEMBL", "DrugBank", "RxNorm", "OMOP"],
    "tissue": ["UBERON", "BTO", "EFO"],
    "cell_line": ["CLO", "Cellosaurus", "EFO"],
    "sample": ["EFO", "OBI"],
    # Extended ontologies for genomic variants and functional annotations
    "variant": ["SO", "ClinVar", "dbSNP", "HGVS", "VCF"],
    "molecular_function": ["GO"],
    "biological_process": ["GO"],
    "cellular_component": ["GO"],
    # OMOP clinical data model entities
    "observation": ["OMOP", "LOINC", "SNOMED"],
    "measurement": ["OMOP", "LOINC", "UCUM"],
    "procedure": ["OMOP", "CPT", "ICD10PCS"],
    "condition": ["OMOP", "ICD10CM", "SNOMED"],
    "visit": ["OMOP"],
    "cohort": ["OMOP", "EFO"],
    # EFO experimental factors
    "experimental_factor": ["EFO", "OBI"],
    "assay": ["EFO", "OBI", "BAO"],
    "sequence_feature": ["SO", "INSDC"],
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
        PropertyDef("gene_type", False, "string"),
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
        PropertyDef("pathway_type", False, "string"),
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
        PropertyDef("drug_type", False, "string"),
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
    # Genomic Variants (SO, ClinVar, dbSNP integration)
    "variant": [
        PropertyDef("variant_id", False, "string"),
        PropertyDef("dbsnp_id", False, "string"),
        PropertyDef("clinvar_id", False, "string"),
        PropertyDef("hgvs_notation", False, "string"),
        PropertyDef("variant_type", False, "string"),  # SNV, indel, CNV, etc.
        PropertyDef("chromosome", False, "string"),
        PropertyDef("start_position", False, "integer"),
        PropertyDef("end_position", False, "integer"),
        PropertyDef("reference_allele", False, "string"),
        PropertyDef("alternate_allele", False, "string"),
        PropertyDef("zygosity", False, "string"),
        PropertyDef("allele_frequency", False, "float"),
        PropertyDef("clinical_significance", False, "string"),
        PropertyDef("pathogenicity", False, "string"),
        PropertyDef("variant_consequence", False, "array"),
        PropertyDef("affected_genes", False, "array"),
        PropertyDef("population_frequencies", False, "array"),
        PropertyDef("functional_predictions", False, "array"),
    ],
    # GO Molecular Function
    "molecular_function": [
        PropertyDef("go_id", False, "string"),
        PropertyDef("function_name", False, "string"),
        PropertyDef("catalytic_activity", False, "string"),
        PropertyDef("binding_activity", False, "string"),
        PropertyDef("molecular_activity", False, "string"),
        PropertyDef("enzyme_class", False, "string"),
        PropertyDef("substrate_specificity", False, "array"),
        PropertyDef("cofactor_requirements", False, "array"),
    ],
    # GO Biological Process
    "biological_process": [
        PropertyDef("go_id", False, "string"),
        PropertyDef("process_name", False, "string"),
        PropertyDef("process_type", False, "string"),
        PropertyDef("regulatory_role", False, "string"),
        PropertyDef("upstream_processes", False, "array"),
        PropertyDef("downstream_processes", False, "array"),
        PropertyDef("participant_molecules", False, "array"),
        PropertyDef("cellular_context", False, "string"),
    ],
    # GO Cellular Component
    "cellular_component": [
        PropertyDef("go_id", False, "string"),
        PropertyDef("component_name", False, "string"),
        PropertyDef("cellular_location", False, "string"),
        PropertyDef("component_type", False, "string"),
        PropertyDef("part_of_components", False, "array"),
        PropertyDef("contains_components", False, "array"),
        PropertyDef("associated_functions", False, "array"),
    ],
    # OMOP Clinical Observations
    "observation": [
        PropertyDef("observation_concept_id", False, "integer"),
        PropertyDef("observation_source_value", False, "string"),
        PropertyDef("observation_date", False, "date"),
        PropertyDef("observation_type", False, "string"),
        PropertyDef("value_as_string", False, "string"),
        PropertyDef("value_as_number", False, "float"),
        PropertyDef("unit_concept_id", False, "integer"),
        PropertyDef("qualifier_concept_id", False, "integer"),
        PropertyDef("provider_id", False, "string"),
        PropertyDef("visit_occurrence_id", False, "string"),
    ],
    # OMOP Measurements
    "measurement": [
        PropertyDef("measurement_concept_id", False, "integer"),
        PropertyDef("measurement_source_value", False, "string"),
        PropertyDef("measurement_date", False, "date"),
        PropertyDef("measurement_type", False, "string"),
        PropertyDef("value_as_number", False, "float"),
        PropertyDef("range_low", False, "float"),
        PropertyDef("range_high", False, "float"),
        PropertyDef("unit_concept_id", False, "integer"),
        PropertyDef("unit_source_value", False, "string"),
        PropertyDef("operator_concept_id", False, "integer"),
    ],
    # OMOP Procedures
    "procedure": [
        PropertyDef("procedure_concept_id", False, "integer"),
        PropertyDef("procedure_source_value", False, "string"),
        PropertyDef("procedure_date", False, "date"),
        PropertyDef("procedure_type", False, "string"),
        PropertyDef("modifier_concept_id", False, "integer"),
        PropertyDef("quantity", False, "integer"),
        PropertyDef("provider_id", False, "string"),
        PropertyDef("visit_occurrence_id", False, "string"),
    ],
    # OMOP Conditions
    "condition": [
        PropertyDef("condition_concept_id", False, "integer"),
        PropertyDef("condition_source_value", False, "string"),
        PropertyDef("condition_start_date", False, "date"),
        PropertyDef("condition_end_date", False, "date"),
        PropertyDef("condition_type", False, "string"),
        PropertyDef("condition_status", False, "string"),
        PropertyDef("stop_reason", False, "string"),
        PropertyDef("provider_id", False, "string"),
        PropertyDef("visit_occurrence_id", False, "string"),
    ],
    # OMOP Visits
    "visit": [
        PropertyDef("visit_concept_id", False, "integer"),
        PropertyDef("visit_start_date", False, "date"),
        PropertyDef("visit_end_date", False, "date"),
        PropertyDef("visit_type", False, "string"),
        PropertyDef("provider_id", False, "string"),
        PropertyDef("care_site_id", False, "string"),
        PropertyDef("visit_source_value", False, "string"),
        PropertyDef("admitted_from_concept_id", False, "integer"),
        PropertyDef("discharged_to_concept_id", False, "integer"),
    ],
    # OMOP/EFO Cohorts
    "cohort": [
        PropertyDef("cohort_definition_id", False, "integer"),
        PropertyDef("cohort_name", False, "string"),
        PropertyDef("cohort_description", False, "string"),
        PropertyDef("definition_type", False, "string"),
        PropertyDef("subject_count", False, "integer"),
        PropertyDef("inclusion_criteria", False, "array"),
        PropertyDef("exclusion_criteria", False, "array"),
        PropertyDef("study_population", False, "string"),
    ],
    # EFO Experimental Factors
    "experimental_factor": [
        PropertyDef("efo_id", False, "string"),
        PropertyDef("factor_name", False, "string"),
        PropertyDef("factor_type", False, "string"),
        PropertyDef("factor_value", False, "string"),
        PropertyDef("unit_of_measurement", False, "string"),
        PropertyDef("experimental_design", False, "string"),
        PropertyDef("treatment_protocol", False, "string"),
        PropertyDef("control_type", False, "string"),
    ],
    # EFO/OBI Assays
    "assay": [
        PropertyDef("assay_id", False, "string"),
        PropertyDef("assay_name", False, "string"),
        PropertyDef("assay_type", False, "string"),
        PropertyDef("technology_type", False, "string"),
        PropertyDef("measurement_type", False, "string"),
        PropertyDef("platform", False, "string"),
        PropertyDef("protocol_description", False, "string"),
        PropertyDef("data_processing_protocol", False, "string"),
        PropertyDef("quality_control_metrics", False, "array"),
    ],
    # SO Sequence Features
    "sequence_feature": [
        PropertyDef("so_id", False, "string"),
        PropertyDef("feature_name", False, "string"),
        PropertyDef("feature_type", False, "string"),
        PropertyDef("sequence_ontology_term", False, "string"),
        PropertyDef("genomic_coordinates", False, "string"),
        PropertyDef("strand", False, "string"),
        PropertyDef("parent_features", False, "array"),
        PropertyDef("child_features", False, "array"),
        PropertyDef("functional_annotation", False, "string"),
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
    
    # Variant relationships (SO, ClinVar, dbSNP)
    if has("variant", "gene"):
        rels.append(RelationDef("Variant", "located_in", "Gene"))
        rels.append(RelationDef("Gene", "has_variant", "Variant"))
        rels.append(RelationDef("Variant", "affects", "Gene"))
    if has("variant", "protein"):
        rels.append(RelationDef("Variant", "affects_protein", "Protein"))
        rels.append(RelationDef("Protein", "altered_by", "Variant"))
    if has("variant", "disease"):
        rels.append(RelationDef("Variant", "associated_with", "Disease"))
        rels.append(RelationDef("Disease", "has_causal_variant", "Variant"))
        rels.append(RelationDef("Variant", "predisposes_to", "Disease"))
    if has("variant", "phenotype"):
        rels.append(RelationDef("Variant", "causes", "Phenotype"))
        rels.append(RelationDef("Phenotype", "caused_by", "Variant"))
    if has("variant", "drug"):
        rels.append(RelationDef("Variant", "affects_drug_response", "Drug"))
        rels.append(RelationDef("Drug", "response_modified_by", "Variant"))
    
    # GO relationships
    if has("protein", "molecular_function"):
        rels.append(RelationDef("Protein", "has_function", "MolecularFunction"))
        rels.append(RelationDef("MolecularFunction", "function_of", "Protein"))
    if has("protein", "biological_process"):
        rels.append(RelationDef("Protein", "participates_in", "BiologicalProcess"))
        rels.append(RelationDef("BiologicalProcess", "has_participant", "Protein"))
    if has("protein", "cellular_component"):
        rels.append(RelationDef("Protein", "located_in", "CellularComponent"))
        rels.append(RelationDef("CellularComponent", "contains", "Protein"))
    if has("gene", "molecular_function"):
        rels.append(RelationDef("Gene", "enables", "MolecularFunction"))
        rels.append(RelationDef("MolecularFunction", "enabled_by", "Gene"))
    if has("molecular_function", "biological_process"):
        rels.append(RelationDef("MolecularFunction", "part_of", "BiologicalProcess"))
        rels.append(RelationDef("BiologicalProcess", "includes", "MolecularFunction"))
    if has("biological_process", "cellular_component"):
        rels.append(RelationDef("BiologicalProcess", "occurs_in", "CellularComponent"))
        rels.append(RelationDef("CellularComponent", "site_of", "BiologicalProcess"))
    
    # OMOP clinical relationships
    if has("observation", "visit"):
        rels.append(RelationDef("Observation", "recorded_during", "Visit"))
        rels.append(RelationDef("Visit", "includes", "Observation"))
    if has("measurement", "visit"):
        rels.append(RelationDef("Measurement", "taken_during", "Visit"))
        rels.append(RelationDef("Visit", "includes", "Measurement"))
    if has("procedure", "visit"):
        rels.append(RelationDef("Procedure", "performed_during", "Visit"))
        rels.append(RelationDef("Visit", "includes", "Procedure"))
    if has("condition", "visit"):
        rels.append(RelationDef("Condition", "diagnosed_during", "Visit"))
        rels.append(RelationDef("Visit", "includes", "Condition"))
    if has("condition", "procedure"):
        rels.append(RelationDef("Condition", "treated_by", "Procedure"))
        rels.append(RelationDef("Procedure", "treats", "Condition"))
    if has("measurement", "condition"):
        rels.append(RelationDef("Measurement", "assesses", "Condition"))
        rels.append(RelationDef("Condition", "measured_by", "Measurement"))
    if has("cohort", "condition"):
        rels.append(RelationDef("Cohort", "has_condition", "Condition"))
        rels.append(RelationDef("Condition", "defines", "Cohort"))
    
    # EFO experimental relationships
    if has("experimental_factor", "assay"):
        rels.append(RelationDef("ExperimentalFactor", "measured_by", "Assay"))
        rels.append(RelationDef("Assay", "measures", "ExperimentalFactor"))
    if has("sample", "experimental_factor"):
        rels.append(RelationDef("Sample", "has_factor", "ExperimentalFactor"))
        rels.append(RelationDef("ExperimentalFactor", "applied_to", "Sample"))
    if has("assay", "measurement"):
        rels.append(RelationDef("Assay", "produces", "Measurement"))
        rels.append(RelationDef("Measurement", "generated_by", "Assay"))
    if has("cohort", "experimental_factor"):
        rels.append(RelationDef("Cohort", "characterized_by", "ExperimentalFactor"))
        rels.append(RelationDef("ExperimentalFactor", "characterizes", "Cohort"))
    
    # Sequence feature relationships (SO)
    if has("sequence_feature", "gene"):
        rels.append(RelationDef("SequenceFeature", "part_of", "Gene"))
        rels.append(RelationDef("Gene", "contains", "SequenceFeature"))
    if has("sequence_feature", "transcript"):
        rels.append(RelationDef("SequenceFeature", "part_of", "Transcript"))
        rels.append(RelationDef("Transcript", "contains", "SequenceFeature"))
    if has("variant", "sequence_feature"):
        rels.append(RelationDef("Variant", "overlaps", "SequenceFeature"))
        rels.append(RelationDef("SequenceFeature", "contains_variant", "Variant"))
    
    # Clinical genomics relationships
    if has("variant", "observation"):
        rels.append(RelationDef("Variant", "observed_as", "Observation"))
        rels.append(RelationDef("Observation", "reports", "Variant"))
    if has("gene", "condition"):
        rels.append(RelationDef("Gene", "associated_with", "Condition"))
        rels.append(RelationDef("Condition", "has_genetic_basis", "Gene"))
    if has("measurement", "gene"):
        rels.append(RelationDef("Measurement", "quantifies_expression", "Gene"))
        rels.append(RelationDef("Gene", "expression_measured_by", "Measurement"))
    
    # Clinical trial relationships (OBI/CDISC/NCIT)
    if has("subject", "investigation"):
        rels.append(RelationDef("Subject", "participates_in", "Investigation"))
        rels.append(RelationDef("Investigation", "enrolls", "Subject"))
    if has("subject", "adverse_event"):
        rels.append(RelationDef("Subject", "experiences", "AdverseEvent"))
        rels.append(RelationDef("AdverseEvent", "affects", "Subject"))
    if has("subject", "demographics"):
        rels.append(RelationDef("Subject", "has_demographics", "Demographics"))
        rels.append(RelationDef("Demographics", "describes", "Subject"))
    if has("subject", "laboratory"):
        rels.append(RelationDef("Subject", "has_lab_result", "Laboratory"))
        rels.append(RelationDef("Laboratory", "measured_for", "Subject"))
    if has("investigation", "protocol"):
        rels.append(RelationDef("Investigation", "follows", "Protocol"))
        rels.append(RelationDef("Protocol", "defines", "Investigation"))
    if has("protocol", "endpoint"):
        rels.append(RelationDef("Protocol", "specifies", "Endpoint"))
        rels.append(RelationDef("Endpoint", "defined_in", "Protocol"))
    if has("investigation", "study_design"):
        rels.append(RelationDef("Investigation", "uses", "StudyDesign"))
        rels.append(RelationDef("StudyDesign", "applied_to", "Investigation"))
    if has("subject", "therapy"):
        rels.append(RelationDef("Subject", "receives", "Therapy"))
        rels.append(RelationDef("Therapy", "administered_to", "Subject"))
    if has("therapy", "biomarker"):
        rels.append(RelationDef("Therapy", "targets", "Biomarker"))
        rels.append(RelationDef("Biomarker", "targeted_by", "Therapy"))
    if has("biomarker", "laboratory"):
        rels.append(RelationDef("Biomarker", "measured_by", "Laboratory"))
        rels.append(RelationDef("Laboratory", "measures", "Biomarker"))
    if has("device", "therapy"):
        rels.append(RelationDef("Device", "delivers", "Therapy"))
        rels.append(RelationDef("Therapy", "delivered_by", "Device"))
    if has("adverse_event", "therapy"):
        rels.append(RelationDef("AdverseEvent", "related_to", "Therapy"))
        rels.append(RelationDef("Therapy", "may_cause", "AdverseEvent"))
    
    # NCIT semantic relationships
    if has("subject", "subject"):  # Handle patient/subject synonymy
        rels.append(RelationDef("Subject", "same_as", "Subject"))  # Self-reference for semantic mapping
    
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
            related["suggested_entities"].extend(["Gene", "Protein", "Phenotype", "Drug", "Sample", "Tissue", "Variant", "Condition", "Observation"])
            related["api_discoveries"].append(f"Disease context detected for {entity} - suggesting genetic, clinical, and molecular entities")
        
        # Drug-based discoveries
        if any(keyword in entity_lower for keyword in ["drug", "compound", "inhibitor", "agonist", "antagonist"]):
            related["suggested_entities"].extend(["Protein", "Disease", "Pathway", "Phenotype", "Variant", "MolecularFunction"])
            related["api_discoveries"].append(f"Drug context detected for {entity} - suggesting target, indication, and pharmacogenomic entities")
        
        # Variant-based discoveries
        if any(keyword in entity_lower for keyword in ["variant", "snp", "mutation", "allele", "genomic"]):
            related["suggested_entities"].extend(["Gene", "Protein", "Disease", "Phenotype", "SequenceFeature"])
            related["api_discoveries"].append(f"Genomic variant context detected for {entity} - suggesting functional and clinical entities")
        
        # Clinical data discoveries
        if any(keyword in entity_lower for keyword in ["clinical", "patient", "hospital", "medical", "diagnosis"]):
            related["suggested_entities"].extend(["Condition", "Procedure", "Observation", "Measurement", "Visit", "Cohort"])
            related["api_discoveries"].append(f"Clinical context detected for {entity} - suggesting OMOP clinical data model entities")
        
        # Experimental data discoveries
        if any(keyword in entity_lower for keyword in ["assay", "experiment", "study", "trial", "screen"]):
            related["suggested_entities"].extend(["ExperimentalFactor", "Assay", "Measurement", "Cohort", "Sample"])
            related["api_discoveries"].append(f"Experimental context detected for {entity} - suggesting EFO experimental design entities")
        
        # Functional annotation discoveries
        if any(keyword in entity_lower for keyword in ["function", "process", "component", "activity", "localization"]):
            related["suggested_entities"].extend(["MolecularFunction", "BiologicalProcess", "CellularComponent", "Protein"])
            related["api_discoveries"].append(f"Functional context detected for {entity} - suggesting GO functional annotation entities")
    
    # Add common biomedical entities based on context
    if any(cat in ["gene", "protein", "disease"] for cat in [_canon(e) for e in entities]):
        related["suggested_entities"].extend(["Sample", "Tissue", "CellLine"])
    
    # Remove duplicates and original entities
    related["suggested_entities"] = list(set(related["suggested_entities"]))
    original_canonical = [_canon(e) for e in entities]
    related["suggested_entities"] = [e for e in related["suggested_entities"] 
                                   if _canon(e) not in original_canonical]
    
    return related

# Main content in tabs for better organization
tab1, tab2 = st.tabs(["🎯 Model Designer", "📝 YAML Editor & Validation"])

with tab2:
    st.markdown("### 📝 Data Model Definition (YAML)")
    st.markdown("**For data architects:** Review and validate your generated data model in YAML format.")
    
    # Initialize model YAML
    if "model_yaml" not in st.session_state:
        st.session_state.model_yaml = default_biolink_skeleton().to_yaml()

    # Check if we have a generated model to display
    if "generated_model_yaml" in st.session_state:
        st.session_state.model_yaml = st.session_state.generated_model_yaml
        del st.session_state.generated_model_yaml

    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.text_area("**Data Model Schema (YAML)**", key="model_yaml", height=500, 
                    help="This YAML defines your complete data model including entities, properties, and relationships.")
    
    with col2:
        st.markdown("#### 🔧 Actions")
        
        if st.button("🔍 Validate Model", type="primary", use_container_width=True):
            try:
                model = IntermediateModel.from_yaml(st.session_state.model_yaml)
                st.success(f"✅ **Model Valid**\n- {len(model.classes)} entity classes\n- {len(model.relations)} relationships")
                st.session_state.model_obj = model
            except Exception as e:
                st.error(f"❌ **Validation Error:** {e}")
        
        if st.button("📊 Generate Summary", use_container_width=True):
            st.session_state.show_summary = True
        
        if st.button("⬇️ Download YAML", use_container_width=True):
            st.download_button(
                label="Download Model",
                data=st.session_state.model_yaml,
                file_name="biomedical_data_model.yaml",
                mime="text/yaml"
            )

    # Model visualization and summary
    if "model_obj" in st.session_state and st.session_state.get("show_summary", False):
        st.markdown("---")
        st.markdown("### 📊 Data Model Summary")
        
        model = st.session_state.model_obj
        
        # Summary cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Entity Classes", len(model.classes))
        with col2:
            st.metric("Relationships", len(model.relations))
        with col3:
            st.metric("Ontologies", len(model.ontologies))
        with col4:
            total_props = sum(len(cls.properties) for cls in model.classes.values())
            st.metric("Total Properties", total_props)
        
        # Entity classes overview
        st.markdown("#### 🗂️ Entity Classes Overview")
        for name, cls in model.classes.items():
            with st.expander(f"**{name}** ({len(cls.properties)} properties)", expanded=False):
                st.markdown(f"*{cls.description}*")
                
                # Properties table with better formatting
                if cls.properties:
                    props_data = []
                    for p in cls.properties:
                        props_data.append({
                            "Property": p.name,
                            "Type": p.datatype,
                            "Required": "✅" if p.required else "➖",
                            "Description": "Core identifier" if p.name == "id" else 
                                         "Domain-specific attribute" if p.datatype != "string" else "Standard attribute"
                        })
                    st.table(props_data)

with tab1:
    st.markdown("### 🎯 Intelligent Model Generation")
    st.markdown("**For data stewards:** Define your core biological entities and let our system generate a comprehensive data model with industry-standard properties and relationships.")
    
    # Step-by-step workflow
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 8px; margin: 1rem 0;">
        <h4 style="color: #495057; margin: 0 0 1rem 0;">📋 Data Modeling Workflow</h4>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="text-align: center; flex: 1;">
                <div style="background: #007bff; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem;">1</div>
                <small><strong>Define Entities</strong><br/>Enter key biological concepts</small>
            </div>
            <div style="color: #dee2e6; font-size: 1.5rem;">→</div>
            <div style="text-align: center; flex: 1;">
                <div style="background: #28a745; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem;">2</div>
                <small><strong>Discover Relations</strong><br/>API-driven entity discovery</small>
            </div>
            <div style="color: #dee2e6; font-size: 1.5rem;">→</div>
            <div style="text-align: center; flex: 1;">
                <div style="background: #ffc107; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem;">3</div>
                <small><strong>Generate Model</strong><br/>Complete schema with properties</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Step 1: Entity Definition
    st.markdown("#### 🔬 Step 1: Define Core Biological Entities")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        entities_text = st.text_input(
            "**Core Entities for Your Data Model**",
            placeholder="Gene, Protein, Disease, Drug, Subject, Investigation, Therapy, Biomarker, AdverseEvent, Demographics",
            help="Enter the main biological and clinical entities relevant to your pharmaceutical data. Supports Biolink, OMOP, GO, SO, EFO, OBI, CDISC, and NCIT standards."
        )
    
    with col2:
        st.markdown("**💡 Extended Pharma & Clinical Entities:**")
        # Organize entities by category
        st.markdown("**🧬 Genomics:** Gene, Protein, Variant, Transcript")
        st.markdown("**🏥 Clinical:** Disease, Phenotype, Condition, Observation")
        st.markdown("**💊 Therapeutics:** Drug, Pathway, MolecularFunction, Therapy, Biomarker")
        st.markdown("**🔬 Experimental:** Sample, Assay, ExperimentalFactor, Investigation")
        st.markdown("**📊 Clinical Data:** Measurement, Procedure, Visit, Cohort, Laboratory")
        st.markdown("**🧩 Functional:** BiologicalProcess, CellularComponent")
        st.markdown("**👥 Clinical Trials:** Subject, Protocol, StudyDesign, Endpoint, AdverseEvent")
        st.markdown("**🏥 CDISC SDTM:** Demographics, VitalSigns, ConcomitantMedication, ECG")
        st.markdown("**🔬 NCIT:** Device, Therapy, Biomarker")

    # Entity preview with professional styling
    if entities_text:
        preview_entities = [e.strip() for e in entities_text.split(",") if e.strip()]
        if preview_entities:
            st.markdown("---")
            st.markdown("#### 📊 Entity Schema Preview")
            st.markdown("*Preview of properties that will be generated for each entity based on Biolink/BioPAX standards:*")
            
            # Create cards for each entity
            cols = st.columns(min(len(preview_entities), 3))
            for i, entity in enumerate(preview_entities[:3]):
                canon_entity = _canon(entity)
                props = _props_for(canon_entity)
                
                with cols[i % 3]:
                    # Professional entity card
                    st.markdown(f"""
                    <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #dee2e6; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h5 style="color: #495057; margin: 0 0 1rem 0; font-weight: 600;">{entity}</h5>
                        <div style="background: #f8f9fa; padding: 0.75rem; border-radius: 4px; margin-bottom: 1rem;">
                            <strong style="color: #007bff;">Entity Type:</strong> <code>{canon_entity}</code>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Property statistics
                    common_count = len(BIOLINK_BIOPAX_PROPS["_common"])
                    specific_count = len(props) - common_count
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Total Properties", len(props))
                    with col_b:
                        st.metric("Domain-Specific", specific_count)
                    
                    # Show key properties
                    if specific_count > 0:
                        st.markdown("**Key Properties:**")
                        specific_props = props[common_count:common_count+3]
                        for prop in specific_props:
                            type_icon = "🔢" if prop.datatype in ["integer", "float"] else "📝" if prop.datatype == "array" else "📄"
                            st.markdown(f"• {type_icon} `{prop.name}`")
                    
                    st.markdown("</div>", unsafe_allow_html=True)

    entered: List[str] = [e for e in [s.strip() for s in entities_text.split(",")] if e] if entities_text else []
    cats: List[str] = [_canon(e) for e in entered]

    if entered:
        st.markdown("---")
        st.markdown("#### 🔍 Step 2: Intelligent Entity Discovery")
        st.markdown("**Leverage APIs and knowledge graphs** to discover related entities and expand your data model scope.")
        
        # Discovery section with professional styling
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div style="background: #e7f3ff; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #007bff;">
                <h5 style="color: #0056b3; margin: 0 0 0.5rem 0;">🧠 Smart Discovery Engine</h5>
                <p style="margin: 0; color: #495057;">Our system will analyze your entities and suggest related biological concepts using:</p>
                <ul style="margin: 0.5rem 0 0 1rem; color: #495057;">
                    <li><strong>Ensembl API</strong> - Gene & transcript relationships</li>
                    <li><strong>UniProt API</strong> - Protein associations</li>
                    <li><strong>Reactome API</strong> - Pathway connections</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("🚀 Discover Related Entities", key="discover_entities", type="primary", use_container_width=True):
                with st.spinner("🔍 Analyzing entities and discovering relationships..."):
                    discovered = _discover_related_entities(entered)
                    
                    if discovered["suggested_entities"]:
                        st.success(f"✅ **Found {len(discovered['suggested_entities'])} related entities!**")
                        
                        # Professional suggestion display
                        st.markdown("#### 💡 Recommended Additional Entities")
                        suggested_cols = st.columns(3)
                        for i, entity in enumerate(discovered["suggested_entities"]):
                            with suggested_cols[i % 3]:
                                st.markdown(f"""
                                <div style="background: #f8f9fa; padding: 0.75rem; border-radius: 4px; margin-bottom: 0.5rem; text-align: center;">
                                    <strong style="color: #28a745;">{entity}</strong>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Allow user to select which discovered entities to add
                        selected_additional = st.multiselect(
                            "**Select entities to include in your data model:**",
                            options=discovered["suggested_entities"],
                            default=discovered["suggested_entities"][:3],  # Select first 3 by default
                            key="selected_additional_entities",
                            help="These entities will be added to your core entities for model generation."
                        )
                        
                        # Update the entities list
                        if selected_additional:
                            all_entities = entered + selected_additional
                            st.markdown(f"""
                            <div style="background: #d4edda; padding: 1rem; border-radius: 4px; border: 1px solid #c3e6cb;">
                                <strong style="color: #155724;">🎯 Enhanced Entity Set:</strong><br/>
                                <span style="color: #495057;">{', '.join(all_entities)}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            # Update the text input in session state for next regeneration
                            st.session_state.discovered_entities = all_entities
                    
                    if discovered["api_discoveries"]:
                        st.markdown("#### 🔬 Discovery Analysis")
                        for discovery in discovered["api_discoveries"]:
                            st.markdown(f"• {discovery}")
                    else:
                        st.warning("⚠️ No additional entities discovered. Try more specific biological terms or check API connectivity.")

        # Use discovered entities if available
        final_entities = st.session_state.get("discovered_entities", entered)
        final_cats = [_canon(e) for e in final_entities]
        
        if final_entities:
            st.markdown("---")
            st.markdown("#### ⚙️ Step 3: Configure Standards & Generate Model")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Recommend ontologies (union of defaults for chosen entities)
                recommended: Set[str] = set()
                for c in final_cats:
                    for o in DEFAULT_ONTS.get(c, []):
                        recommended.add(o)
                
                st.markdown("**🔬 Biomedical Ontology Standards**")
                selected_onts = st.multiselect(
                    "Select ontologies for your data model",
                    options=sorted(list(recommended)),
                    default=sorted(list(recommended)),
                    key="model_helper_onts",
                    help="These ontologies will provide standardized identifiers and classifications for your entities."
                )
                
                # Optional OLS search
                with st.expander("🔍 Advanced: Search Ontology Lookup Service (OLS)", expanded=False):
                    st.markdown("*Search for specific ontology terms to validate your entity choices:*")
                    q = st.text_input("Search terms", value=(entered[0] if entered else ""), key="ols_q")
                    if q:
                        try:
                            hits = search_ontology_terms(q, size=10)
                            if hits:
                                st.table([
                                    {
                                        "Label": h.get("label"),
                                        "Ontology": h.get("ontology_name"),
                                        "IRI": h.get("iri"),
                                    }
                                    for h in hits
                                ])
                            else:
                                st.info("No OLS results found.")
                        except Exception as e:
                            st.warning(f"OLS search failed: {e}")

            with col2:
                st.markdown("**📊 Model Summary**")
                
                # Preview of what will be generated
                total_props = sum(len(_props_for(cat)) for cat in final_cats)
                relationships = len(_suggest_relations(set(final_cats)))
                
                st.metric("Entities", len(final_entities))
                st.metric("Properties", total_props)
                st.metric("Relationships", relationships)
                st.metric("Ontologies", len(selected_onts))
                
                # Generate button with professional styling
                if st.button("🎯 Generate Data Model", key="generate_model", type="primary", use_container_width=True):
                    with st.spinner("🔧 Generating comprehensive data model..."):
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
                        st.session_state.model_obj = model
                        st.success("✅ **Data model generated successfully!** Switch to the YAML Editor tab to review and validate.")
                        st.rerun()