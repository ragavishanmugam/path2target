from __future__ import annotations

import streamlit as st
import pandas as pd
from path2target.apis import EnsemblAPI, UniProtAPI, PDBAPI, ReactomeAPI, safe_api_call
from path2target.resolvers import resolve_to_ensembl_gene

st.title("Central Dogma Navigator")
st.caption("Gene ID → Transcripts → Proteins → Pathways")

# Input supports Ensembl ID, HGNC symbol, gene name, etc.
user_query = st.text_input("Enter gene (HGNC symbol, gene name, Ensembl ID, etc.)", value="TP53")

if st.button("Trace Gene Flow") and user_query:
    with st.spinner("Fetching data from APIs..."):
        # Resolve input to Ensembl gene ID
        resolved = resolve_to_ensembl_gene(user_query)
        if not resolved:
            st.error("Could not resolve input to an Ensembl Gene ID. Try a different identifier.")
            st.stop()
        gene_id = resolved["ensembl_gene_id"]
        gene_name = resolved.get("symbol", "")

        # 1. Gene Info
        st.subheader("🧬 Gene")
        gene_info = safe_api_call(EnsemblAPI.get_gene_info, gene_id)
        if gene_info:
            st.json({
                "ID": gene_info.get("id"),
                "Name": gene_info.get("display_name"),
                "Description": gene_info.get("description", ""),
                "Biotype": gene_info.get("biotype"),
                "Location": f"{gene_info.get('seq_region_name')}:{gene_info.get('start')}-{gene_info.get('end')}"
            })
            gene_name = gene_name or gene_info.get("display_name", "")
        else:
            st.error("Gene not found")
            st.stop()
        
        # 2. Transcripts
        st.subheader("📜 RNA (Transcripts)")
        transcripts = safe_api_call(EnsemblAPI.get_transcripts, gene_id)
        if transcripts:
            transcript_data = []
            for t in transcripts[:10]:  # Limit to 10
                transcript_data.append({
                    "Transcript ID": t.get("id"),
                    "Biotype": t.get("biotype"),
                    "Length": t.get("length"),
                    "Is Canonical": t.get("is_canonical", False)
                })
            st.dataframe(pd.DataFrame(transcript_data))
        else:
            st.warning("No transcripts found")
        
        # 3. Proteins
        st.subheader("🧬 Proteins")
        if gene_name:
            proteins = safe_api_call(UniProtAPI.get_proteins_by_gene, gene_name)
            if proteins:
                protein_data = []
                uniprot_ids = []
                for p in proteins[:10]:  # Limit to 10
                    uniprot_id = p.get("primaryAccession")
                    uniprot_ids.append(uniprot_id)
                    # Fetch extra details (EC numbers, recommended/short names)
                    details = safe_api_call(UniProtAPI.get_protein_details, uniprot_id) or {}
                    ec_numbers = []
                    for ann in details.get("proteinDescription", {}).get("recommendedName", {}).get("ecNumbers", []) or []:
                        val = ann.get("value")
                        if val:
                            ec_numbers.append(val)
                    protein_data.append({
                        "UniProt ID": uniprot_id,
                        "Protein Name": p.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
                        "Length": p.get("sequence", {}).get("length"),
                        "Gene Names": ", ".join([g.get("geneName", {}).get("value", "") for g in p.get("genes", [])]),
                        "EC": ", ".join(ec_numbers),
                        "UniProt URL": f"https://www.uniprot.org/uniprotkb/{uniprot_id}"
                    })
                st.dataframe(pd.DataFrame(protein_data))
                
                # 4. PDB Structures
                st.subheader("🏗️ PDB Structures")
                all_structures = []
                for uniprot_id in uniprot_ids[:3]:  # Check first 3 proteins
                    structures = safe_api_call(PDBAPI.get_structures_by_uniprot, uniprot_id) or []
                    for s in structures[:5]:  # Limit to 5 per protein
                        pid = None
                        if isinstance(s, dict):
                            pid = s.get("identifier") or s.get("entry_id") or s.get("entryId")
                        elif isinstance(s, str):
                            pid = s
                        if pid:
                            all_structures.append({
                                "PDB ID": pid,
                                "UniProt": uniprot_id
                            })
                
                if all_structures:
                    st.dataframe(pd.DataFrame(all_structures))
                else:
                    st.info("No PDB structures found")
                
                # 5. Pathways
                st.subheader("🛤️ Pathways (Reactome)")
                all_pathways = []
                for uniprot_id in uniprot_ids[:3]:  # Check first 3 proteins
                    pathways = safe_api_call(ReactomeAPI.get_pathways_by_protein, uniprot_id)
                    for p in pathways[:10]:  # Limit to 10 per protein
                        is_enzyme = False
                        relation = "participates in"
                        # If UniProt record has EC numbers, treat as enzyme (catalyzes)
                        # We already looked up details earlier; this is a heuristic
                        if any(row.get("UniProt ID") == uniprot_id and row.get("EC") for row in protein_data):
                            is_enzyme = True
                            relation = "catalyzes in"
                        all_pathways.append({
                            "Pathway ID": p.get("stId"),
                            "Pathway Name": p.get("displayName"),
                            "Species": p.get("speciesName"),
                            "UniProt": uniprot_id,
                            "Relation": relation,
                            "Reactome URL": f"https://reactome.org/PathwayBrowser/#/{p.get('stId')}"
                        })
                
                if all_pathways:
                    st.dataframe(pd.DataFrame(all_pathways))
                else:
                    st.info("No Reactome pathways found")
            else:
                st.warning("No proteins found for this gene")
        else:
            st.warning("Gene name required for protein lookup")

st.divider()
st.subheader("📊 API Sources")
st.write("- **Ensembl REST API**: Gene info and transcripts")
st.write("- **UniProt REST API**: Protein sequences and annotations") 
st.write("- **PDB Search API**: 3D structure data")
st.write("- **Reactome Content Service**: Biological pathways")


