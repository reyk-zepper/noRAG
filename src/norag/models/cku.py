"""Compiled Knowledge Unit (CKU) — Pydantic v2 models and YAML serialization."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    page: Optional[int] = None
    section: Optional[str] = None


class Relation(BaseModel):
    target: str
    type: str


class SectionSummary(BaseModel):
    id: str
    title: str
    summary: str


class CKUMeta(BaseModel):
    source: str
    compiled: datetime
    hash: str
    type: str  # "pdf/multimodal", "markdown", etc.
    language: str = "en"


class CKUSummary(BaseModel):
    document: str
    sections: list[SectionSummary] = Field(default_factory=list)


class CKUEntity(BaseModel):
    id: str
    name: str
    type: str  # "person", "process", "system", "concept", etc.
    relations: list[Relation] = Field(default_factory=list)


class CKUFact(BaseModel):
    id: str
    claim: str
    source: SourceRef
    confidence: float = 1.0
    entities: list[str] = Field(default_factory=list)


class CKUVisual(BaseModel):
    id: str
    type: str  # "flowchart", "table", "diagram", "image"
    source: SourceRef
    description: str
    structured_data: Optional[dict[str, Any]] = None
    context: Optional[str] = None


class CKU(BaseModel):
    meta: CKUMeta
    summaries: CKUSummary
    entities: list[CKUEntity] = Field(default_factory=list)
    facts: list[CKUFact] = Field(default_factory=list)
    visuals: list[CKUVisual] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)

    def to_yaml(self) -> str:
        """Serialize CKU to a YAML string."""
        data = self.model_dump(mode="json")
        return yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)

    @classmethod
    def from_yaml(cls, text: str) -> "CKU":
        """Deserialize a CKU from a YAML string."""
        data = yaml.safe_load(text)
        return cls.model_validate(data)
