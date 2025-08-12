# path2target

Automated transformation engine for biomedical knowledge graphs. Ingest PRIME-KG and other sources, infer schemas, map to a Biolink/BioPAX-compatible intermediate model, normalize identifiers via OLS/Ensembl/UniProt, and export validated RDF/JSON-LD/TSV ready for DISQOVER.

## MVP Pages
- Central Dogma Navigator (DNA → RNA → Protein → Pathways)
- Raw Layer (ingest + schema understanding)
- Intermediate Layer (model designer)
- Transformation & Output (RDF/JSON-LD/TSV + SHACL validation)

## Quickstart
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

streamlit run app/Home.py
```

## CLI
```bash
path2t ingest --source primekg --url https://example/primekg/kg.csv --out data/raw/primekg.csv
path2t transform --config configs/mappings/example.yaml --out outputs/
```


