from __future__ import annotations

from typing import Dict
import textwrap


def get_available_sources() -> list[str]:
    return [
        "cBioPortal",
        "GEO (Series Matrix)",
        "PandaOmics (stub)",
    ]


def get_metadata_definition(source: str) -> str:
    """Return a YAML-like template describing required inputs/metadata for a public source.

    This is intended as a starting point the user can edit and save.
    """
    s = source.lower()
    if s.startswith("cbio"):
        return textwrap.dedent(
            """
            source: cBioPortal
            description: |
              Standard cBioPortal study data files and their expected schemas. See cBioPortal
              File Formats docs. This profile captures the core files commonly required.
            files:
              - name: meta_study.txt
                required: true
                format: keyvalue
                fields:
                  - {name: type_of_cancer, required: true, example: "brca"}
                  - {name: name, required: true}
                  - {name: description, required: true}
                  - {name: short_name, required: false}
                  - {name: pmid, required: false}
              - name: meta_clinical_sample.txt
                required: true
                format: keyvalue
                fields:
                  - {name: genetic_alteration_type, value: CLINICAL}
                  - {name: datatype, value: SAMPLE_ATTRIBUTES}
                  - {name: data_filename, required: true, example: data_clinical_sample.txt}
              - name: data_clinical_sample.txt
                required: true
                format: tsv
                columns:
                  - {name: SAMPLE_ID, type: string, required: true}
                  - {name: PATIENT_ID, type: string, required: true}
                  - {name: CANCER_TYPE, type: string}
                  - {name: SAMPLE_TYPE, type: string}
                  - {name: AGE, type: number}
                  - {name: SEX, type: string, enum: [MALE, FEMALE]}
              - name: meta_mutations_extended.txt
                required: false
                format: keyvalue
                fields:
                  - {name: genetic_alteration_type, value: MUTATION_EXTENDED}
                  - {name: datatype, value: MAF}
                  - {name: data_filename, required: true, example: data_mutations_extended.txt}
              - name: data_mutations_extended.txt
                required: false
                format: maf
                columns:
                  - {name: Hugo_Symbol, type: string, required: true}
                  - {name: Entrez_Gene_Id, type: integer}
                  - {name: Tumor_Sample_Barcode, type: string, required: true}
                  - {name: Variant_Classification, type: string}
                  - {name: HGVSp_Short, type: string}
            mapping_hints:
              entity_types:
                - Patient
                - Sample
                - Mutation
              identifiers:
                - HGNC Symbol
                - Entrez Gene Id
            """
        ).strip()

    if s.startswith("geo"):
        return textwrap.dedent(
            """
            source: GEO (Series Matrix)
            description: |
              GEO Series Matrix processed expression table with metadata. Expect a single TXT.GZ containing
              a table between !series_matrix_table_begin and !series_matrix_table_end.
            files:
              - name: <GSE>_series_matrix.txt.gz
                required: true
                format: geo_series_matrix
                columns:
                  - {name: ID_REF, role: gene_identifier}
                  - {name: <GSM sample columns>, role: sample_expression_values}
            metadata:
              sample:
                required_fields: [sample_id]
                suggested_fields: [title, source_name_ch1, characteristics_ch1]
              mapping_suggestions:
                - {from: characteristics_ch1, to: group, rule: parse "<key>: <value>" pairs}
            """
        ).strip()

    # Stub for PandaOmics or other proprietary sources
    return textwrap.dedent(
        """
        source: PandaOmics (stub)
        description: |
          Define the input formats exported from PandaOmics (e.g., differential expression tables,
          signatures). Fill in column names, types, and identifier standards used.
        files:
          - name: exported_results.csv
            required: true
            format: csv
            columns:
              - {name: gene, type: string, id_namespace: HGNC Symbol}
              - {name: log2FC, type: number}
              - {name: pvalue, type: number}
              - {name: padj, type: number}
        """
    ).strip()


