from __future__ import annotations

import streamlit as st
import pandas as pd
from path2target.apis import EnsemblAPI, UniProtAPI, PDBAPI, ReactomeAPI, safe_api_call
from path2target.resolvers import resolve_to_ensembl_gene
import plotly.graph_objects as go

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
            ens_gene_url = f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={gene_info.get('id')}"
            st.markdown(
                f"**ID**: [{gene_info.get('id')}]({ens_gene_url})  |  **Name**: {gene_info.get('display_name')}  |  **Biotype**: {gene_info.get('biotype')}\n\n"
                f"**Location**: {gene_info.get('seq_region_name')}:{gene_info.get('start')}-{gene_info.get('end')}\n\n"
                f"**Description**: {gene_info.get('description', '')}"
            )
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
            # Add Ensembl transcript links
            df_t = pd.DataFrame(transcript_data)
            df_t["Link"] = df_t["Transcript ID"].apply(
                lambda tid: f"https://www.ensembl.org/Homo_sapiens/Transcript/Summary?t={tid}"
            )
            st.dataframe(
                df_t,
                hide_index=True,
                column_config={
                    "Link": st.column_config.LinkColumn("Ensembl", help="Open transcript in Ensembl"),
                },
            )
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
                    # Fetch extra details (EC numbers) defensively (Cloud may use cached module)
                    details_func = getattr(UniProtAPI, "get_protein_details", None)
                    details = safe_api_call(details_func, uniprot_id) if callable(details_func) else {}
                    # EC from details or from search result fallback
                    ec_numbers = []
                    for ann in (details.get("proteinDescription", {}).get("recommendedName", {}).get("ecNumbers", []) or []):
                        val = ann.get("value")
                        if val:
                            ec_numbers.append(val)
                    if not ec_numbers:
                        for ann in (p.get("proteinDescription", {}).get("recommendedName", {}).get("ecNumbers", []) or []):
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
                df_p = pd.DataFrame(protein_data)
                # Create clickable link column (keep ID column too)
                df_p["Link"] = df_p["UniProt URL"]
                st.dataframe(
                    df_p,
                    hide_index=True,
                    column_config={
                        "Link": st.column_config.LinkColumn("UniProt", help="Open UniProt record"),
                    },
                )
                
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
                            get_entry_details = getattr(PDBAPI, "get_entry_details", None)
                            det = safe_api_call(get_entry_details, pid) if callable(get_entry_details) else {}
                            # Parse method and resolution defensively
                            methods = []
                            for d in (det.get("exptl") or []):
                                if isinstance(d, dict) and d.get("method"):
                                    methods.append(d.get("method"))
                            method_str = ", ".join(methods)
                            res_list = det.get("rcsb_entry_info", {}).get("resolution_combined") or []
                            resolution = str(res_list[0]) if res_list else ""
                            all_structures.append({
                                "PDB ID": pid,
                                "Title": det.get("struct", {}).get("title", ""),
                                "Method": method_str,
                                "Resolution": resolution,
                                "URL": f"https://www.rcsb.org/structure/{pid}",
                                "UniProt": uniprot_id,
                            })
                
                if all_structures:
                    df_s = pd.DataFrame(all_structures)
                    # Ensure there is a generic Link column
                    if "URL" in df_s.columns:
                        df_s["Link"] = df_s["URL"]
                    st.dataframe(
                        df_s,
                        hide_index=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("PDB", help="Open PDB entry"),
                        },
                    )
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
                        stid = p.get("stId")
                        get_pathway_details = getattr(ReactomeAPI, "get_pathway_details", None)
                        pdet = safe_api_call(get_pathway_details, stid) if (callable(get_pathway_details) and stid) else {}
                        all_pathways.append({
                            "Pathway ID": stid,
                            "Pathway Name": p.get("displayName"),
                            "Species": p.get("speciesName"),
                            "Relation": relation,
                            "Top Level?": pdet.get("isTopLevelPathway", False) if isinstance(pdet, dict) else False,
                            "Reactome URL": f"https://reactome.org/PathwayBrowser/#/{stid}",
                            "UniProt": uniprot_id,
                        })
                
                if all_pathways:
                    df_pw = pd.DataFrame(all_pathways)
                    df_pw["Link"] = df_pw["Reactome URL"]
                    st.dataframe(
                        df_pw,
                        hide_index=True,
                        column_config={
                            "Link": st.column_config.LinkColumn("Reactome", help="Open pathway in Reactome"),
                        },
                    )
                else:
                    st.info("No Reactome pathways found")

                # ----- Central Dogma Interactive (Sankey) -----
                st.subheader("Central Dogma Overview")
                tx_ids = [t.get("Transcript ID") for t in (pd.DataFrame(transcript_data).to_dict("records") if transcript_data else [])]
                prot_ids = list(uniprot_ids or [])
                pw_ids = [row.get("Pathway ID") for row in (all_pathways or []) if row.get("Pathway ID")]

                # Build Sankey nodes and links
                node_labels = [
                    f"Gene: {gene_name or gene_id}",
                    "RNA (Transcripts)",
                    "Proteins",
                    "Pathways",
                ]
                sources = [0, 1, 2]
                targets = [1, 2, 3]
                values = [max(len(tx_ids), 1), max(len(prot_ids), 1), max(len(pw_ids), 1)]
                examples = [
                    ", ".join((tx_ids or [])[:5]),
                    ", ".join((prot_ids or [])[:5]),
                    ", ".join((pw_ids or [])[:5]),
                ]

                link_custom = [f"Examples: {ex}" if ex else "Examples: None" for ex in examples]
                fig = go.Figure(
                    data=[
                        go.Sankey(
                            node=dict(
                                pad=18,
                                thickness=18,
                                line=dict(color="#888", width=0.5),
                                label=node_labels,
                            ),
                            link=dict(
                                source=sources,
                                target=targets,
                                value=values,
                                customdata=link_custom,
                                hovertemplate="%{customdata}<extra></extra>",
                            ),
                        )
                    ]
                )
                fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True, theme="streamlit")
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


