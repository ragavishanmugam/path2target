from __future__ import annotations

from typing import Dict, List, Optional
import requests
import time


class EnsemblAPI:
    BASE_URL = "https://rest.ensembl.org"
    
    @staticmethod
    def get_gene_info(gene_id: str) -> Dict:
        """Get gene information from Ensembl."""
        url = f"{EnsemblAPI.BASE_URL}/lookup/id/{gene_id}"
        headers = {"Content-Type": "application/json"}
        
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()
    
    @staticmethod
    def get_transcripts(gene_id: str) -> List[Dict]:
        """Get all transcripts for a gene."""
        url = f"{EnsemblAPI.BASE_URL}/lookup/id/{gene_id}"
        headers = {"Content-Type": "application/json"}
        params = {"expand": "1"}
        
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        return data.get("Transcript", [])


class UniProtAPI:
    BASE_URL = "https://rest.uniprot.org"
    
    @staticmethod
    def get_proteins_by_gene(gene_name: str) -> List[Dict]:
        """Get UniProt proteins for a gene name."""
        url = f"{UniProtAPI.BASE_URL}/uniprotkb/search"
        params = {
            "query": f"gene:{gene_name} AND organism_id:9606",
            "format": "json",
            "size": "25"
        }
        
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("results", [])

    @staticmethod
    def get_protein_details(accession: str) -> Dict:
        """Fetch rich UniProt record for an accession (for EC numbers, names, etc.)."""
        try:
            url = f"{UniProtAPI.BASE_URL}/uniprotkb/{accession}.json"
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            return {}


class PDBAPI:
    BASE_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
    
    @staticmethod
    def get_structures_by_uniprot(uniprot_id: str) -> List[Dict]:
        """Get PDB structures for a UniProt ID.

        Returns a list of dicts with at least a 'identifier' key when available.
        """
        query = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                    "operator": "exact_match",
                    "value": uniprot_id
                }
            },
            "return_type": "entry",
            "request_options": {
                "return_all_hits": False,
                "results_verbosity": "compact"
            }
        }
        
        try:
            r = requests.post(PDBAPI.BASE_URL, json=query, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception:
            return []

        items = data.get("result_set") or data.get("resultSet") or []
        results: List[Dict] = []
        for item in items:
            if isinstance(item, dict):
                pid = item.get("identifier") or item.get("entry_id") or item.get("entryId")
                if isinstance(pid, str) and pid:
                    results.append({"identifier": pid})
            elif isinstance(item, str):
                results.append({"identifier": item})
        return results


class ReactomeAPI:
    BASE_URL = "https://reactome.org/ContentService"
    
    @staticmethod
    def get_pathways_by_protein(uniprot_id: str) -> List[Dict]:
        """Get Reactome pathways for a protein."""
        url = f"{ReactomeAPI.BASE_URL}/data/pathways/low/entity/{uniprot_id}/allForms"
        params = {"species": "9606"}  # Human
        
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            return []


def safe_api_call(func, *args, **kwargs):
    """Wrapper for safe API calls with retry logic."""
    for attempt in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == 2:  # Last attempt
                print(f"API call failed after 3 attempts: {e}")
                return []
            time.sleep(1)  # Wait before retry
    return []
