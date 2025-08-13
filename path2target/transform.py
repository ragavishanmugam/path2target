from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pandas as pd
import yaml
from rdflib import Graph, Namespace, RDF, RDFS, URIRef, Literal


def run_transformations(config: Path, outdir: Path) -> Dict[str, Any]:
    """Run simple field mapping to RDF/JSON-LD/TSV based on a YAML config.

    Config shape (example):
    dataset:
      path: data/raw/input.csv
    mapping:
      entity: Gene
      id: gene_id
      label: gene_name
      type_iri: http://w3id.org/biolink/vocab/Gene
    """
    cfg = yaml.safe_load(config.read_text())
    df = pd.read_csv(cfg["dataset"]["path"]) if "path" in cfg["dataset"] else pd.DataFrame()

    g = Graph()
    BL = Namespace("https://w3id.org/biolink/vocab/")
    g.bind("biolink", BL)

    rows = []
    for _, row in df.iterrows():
        curie = str(row[cfg["mapping"]["id"]])
        label = str(row.get(cfg["mapping"].get("label", ""), ""))
        iri = URIRef(cfg["mapping"].get("base_iri", "http://example.org/") + curie)
        type_iri = URIRef(cfg["mapping"].get("type_iri", str(BL[cfg["mapping"].get("entity", "Entity")])))
        g.add((iri, RDF.type, type_iri))
        if label:
            g.add((iri, RDFS.label, Literal(label)))
        rows.append({"id": curie, "label": label, "type": str(type_iri)})

    # Write outputs
    ttl_path = outdir / "export.ttl"
    g.serialize(destination=str(ttl_path), format="turtle")
    (outdir / "export.jsonld").write_text(g.serialize(format="json-ld", indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(outdir / "export.tsv", sep="\t", index=False)

    return {"num_triples": len(g), "num_rows": len(rows)}



