from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml


@dataclass
class PropertyDef:
    name: str
    required: bool = False
    datatype: str = "string"


@dataclass
class EntityClass:
    name: str
    description: str = ""
    properties: List[PropertyDef] = field(default_factory=list)


@dataclass
class RelationDef:
    subject: str
    predicate: str
    object: str


@dataclass
class IntermediateModel:
    classes: Dict[str, EntityClass] = field(default_factory=dict)
    relations: List[RelationDef] = field(default_factory=list)
    ontologies: List[str] = field(default_factory=list)

    def to_yaml(self) -> str:
        data = {
            "classes": {
                name: {
                    "description": cls.description,
                    "properties": [p.__dict__ for p in cls.properties],
                }
                for name, cls in self.classes.items()
            },
            "relations": [r.__dict__ for r in self.relations],
            "ontologies": self.ontologies,
        }
        return yaml.safe_dump(data, sort_keys=False)

    @staticmethod
    def from_yaml(text: str) -> "IntermediateModel":
        data = yaml.safe_load(text) or {}
        classes = {}
        for name, c in (data.get("classes") or {}).items():
            classes[name] = EntityClass(
                name=name,
                description=c.get("description", ""),
                properties=[PropertyDef(**p) for p in (c.get("properties") or [])],
            )
        relations = [RelationDef(**r) for r in (data.get("relations") or [])]
        ontologies = data.get("ontologies") or []
        return IntermediateModel(classes=classes, relations=relations, ontologies=ontologies)


def default_biolink_skeleton() -> IntermediateModel:
    model = IntermediateModel()
    # Minimal skeleton
    model.classes["Gene"] = EntityClass("Gene", properties=[PropertyDef("id", True), PropertyDef("name")])
    model.classes["Transcript"] = EntityClass("Transcript", properties=[PropertyDef("id", True), PropertyDef("name")])
    model.classes["Protein"] = EntityClass("Protein", properties=[PropertyDef("id", True), PropertyDef("name")])
    model.classes["Pathway"] = EntityClass("Pathway", properties=[PropertyDef("id", True), PropertyDef("name")])
    model.relations.append(RelationDef("Gene", "transcribes_to", "Transcript"))
    model.relations.append(RelationDef("Transcript", "translates_to", "Protein"))
    model.relations.append(RelationDef("Protein", "participates_in", "Pathway"))
    model.ontologies = ["GO", "MONDO", "HPO", "CHEBI"]
    return model



