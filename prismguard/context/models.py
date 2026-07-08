from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Sensitivity = Literal["public", "internal", "restricted"]
EntityType = Literal[
    "client_name",
    "matter_id",
    "patient_id",
    "account_id",
    "product_name",
    "legal_concept",
    "medical_term",
    "financial_term",
    "policy_id",
    "generic",
]


class EntityTerm(BaseModel):
    term: str
    type: EntityType = "generic"
    sensitivity: Sensitivity = "internal"
    aliases: list[str] = Field(default_factory=list)


class TenantLexicon(BaseModel):
    """Optional tenant vocabulary for domain-aware guarding."""

    domain: str = "general"
    source: str = ""
    entities: list[EntityTerm] = Field(default_factory=list)
    override_tokens: list[str] = Field(default_factory=list)

    def all_terms(self) -> list[tuple[str, EntityTerm]]:
        rows: list[tuple[str, EntityTerm]] = []
        for entity in self.entities:
            rows.append((entity.term, entity))
            for alias in entity.aliases:
                rows.append((alias, entity))
        return rows

    def restricted_terms(self) -> list[str]:
        return [
            term
            for term, entity in self.all_terms()
            if entity.sensitivity == "restricted"
        ]
