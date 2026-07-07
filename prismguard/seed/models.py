from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["critical", "high", "medium", "low"]
PatternType = Literal["regex", "keyword"]


@dataclass
class CategorySeed:
    slug: str
    label: str
    description: str = ""
    is_attack_category: bool = True
    bridges_to: list[str] = field(default_factory=list)
    source_file: str = ""


@dataclass
class RuleSeed:
    rule_id: str
    pattern: str
    pattern_type: PatternType
    category_slug: str
    severity: Severity
    rationale: str = ""
    created_by: str = ""
    source_file: str = ""


@dataclass
class EntrySeed:
    text: str = ""
    category_slug: str = ""
    severity: Severity = "medium"
    source: str = "import"
    rule_id: str | None = None
    notes: str | None = None
    source_file: str = ""
    turns: list[str] | None = None

    secondary_category_slugs: list[str] = field(default_factory=list)

    def canonical_text(self) -> str:
        """Single string used for normalization, hashing, and storage."""
        if self.turns:
            return "\n---TURN---\n".join(t.strip() for t in self.turns if t.strip())
        return self.text.strip()


@dataclass
class ParsedSeed:
    categories: list[CategorySeed] = field(default_factory=list)
    rules: list[RuleSeed] = field(default_factory=list)
    entries: list[EntrySeed] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)

    def with_source(self, source_file: str) -> ParsedSeed:
        return ParsedSeed(
            categories=[CategorySeed(**{**c.__dict__, "source_file": source_file}) for c in self.categories],
            rules=[RuleSeed(**{**r.__dict__, "source_file": source_file}) for r in self.rules],
            entries=[EntrySeed(**{**e.__dict__, "source_file": source_file}) for e in self.entries],
            source_files=[*self.source_files, source_file],
        )
