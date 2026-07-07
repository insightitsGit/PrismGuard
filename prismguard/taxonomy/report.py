from __future__ import annotations

from dataclasses import dataclass, field

from prismguard.seed.models import ParsedSeed
from prismguard.storage.protocols import StorageBackend
from prismguard.taxonomy.ingest import iter_all_seed_entries
from prismguard.taxonomy.mapping import TaxonomyEngine


@dataclass
class CategoryCoverage:
    slug: str
    label: str
    is_attack_category: bool
    seed_entries: int = 0
    stored_entries: int = 0
    embedded_entries: int = 0
    tier1_rules: int = 0
    keyword_rules: int = 0
    bridges: list[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    categories: list[CategoryCoverage]
    total_seed_entries: int
    total_stored: int
    total_embedded: int
    attack_categories: int
    uncovered_attack_categories: list[str] = field(default_factory=list)
    unembedded_entries: int = 0

    def to_dict(self) -> dict:
        return {
            "total_seed_entries": self.total_seed_entries,
            "total_stored": self.total_stored,
            "total_embedded": self.total_embedded,
            "attack_categories": self.attack_categories,
            "uncovered_attack_categories": self.uncovered_attack_categories,
            "unembedded_entries": self.unembedded_entries,
            "categories": [
                {
                    "slug": c.slug,
                    "label": c.label,
                    "is_attack_category": c.is_attack_category,
                    "seed_entries": c.seed_entries,
                    "stored_entries": c.stored_entries,
                    "embedded_entries": c.embedded_entries,
                    "tier1_rules": c.tier1_rules,
                    "keyword_rules": c.keyword_rules,
                    "bridges": c.bridges,
                }
                for c in self.categories
            ],
        }


def build_coverage_report(
    storage: StorageBackend,
    parsed: ParsedSeed,
    engine: TaxonomyEngine,
) -> CoverageReport:
    seed_by_cat: dict[str, int] = {}
    for entry in parsed.entries:
        seed_by_cat[entry.category_slug] = seed_by_cat.get(entry.category_slug, 0) + 1

    rules_by_cat: dict[str, int] = {}
    for rule in parsed.rules:
        rules_by_cat[rule.category_slug] = rules_by_cat.get(rule.category_slug, 0) + 1

    stored_by_cat: dict[str, list] = {}
    for entry in iter_all_seed_entries(storage):
        stored_by_cat.setdefault(entry.category_slug, []).append(entry)

    categories: list[CategoryCoverage] = []
    uncovered: list[str] = []

    for category in parsed.categories:
        stored = stored_by_cat.get(category.slug, [])
        embedded = sum(1 for e in stored if e.embedding_semantic and e.embedding_category)
        cov = CategoryCoverage(
            slug=category.slug,
            label=category.label,
            is_attack_category=category.is_attack_category,
            seed_entries=seed_by_cat.get(category.slug, 0),
            stored_entries=len(stored),
            embedded_entries=embedded,
            tier1_rules=rules_by_cat.get(category.slug, 0),
            keyword_rules=sum(
                1 for r in parsed.rules if r.category_slug == category.slug and r.pattern_type == "keyword"
            ),
            bridges=list(category.bridges_to),
        )
        categories.append(cov)
        if category.is_attack_category and cov.seed_entries > 0 and cov.stored_entries == 0:
            uncovered.append(category.slug)

    total_stored = sum(c.stored_entries for c in categories)
    total_embedded = sum(c.embedded_entries for c in categories)
    attack_count = sum(1 for c in categories if c.is_attack_category)

    return CoverageReport(
        categories=categories,
        total_seed_entries=len(parsed.entries),
        total_stored=total_stored,
        total_embedded=total_embedded,
        attack_categories=attack_count,
        uncovered_attack_categories=uncovered,
        unembedded_entries=total_stored - total_embedded,
    )


def estimate_llm_reduction(coverage: CoverageReport) -> dict[str, float | str]:
    """
    Architectural estimate of traffic resolved before LLM judge (Part I gates).
    Percentages are design targets when all Part D layers are active; current
    implementation resolves tier1 + corpus ANN + benign fast-path without LLM.
    """
    has_rules = sum(c.tier1_rules for c in coverage.categories)
    has_corpus = coverage.total_embedded > 0
    tier1_pct = 12.0 if has_rules else 0.0
    structural_pct = 8.0
    benign_pct = 35.0 if has_corpus else 0.0
    corpus_pct = 38.0 if has_corpus else 0.0
    guard_pct = 5.0
    llm_pct = max(0.0, 100.0 - tier1_pct - structural_pct - benign_pct - corpus_pct - guard_pct)

    return {
        "tier1_rule_pct": tier1_pct,
        "structural_pct": structural_pct,
        "benign_fast_path_pct": benign_pct,
        "corpus_ann_fusion_pct": corpus_pct,
        "guard_model_pct": guard_pct,
        "llm_judge_pct": round(llm_pct, 1),
        "note": (
            "Estimates assume full Part D (T8–T9). Current code: tier1 + ANN fusion + "
            "benign fast-path active; structural/session/guard/LLM not yet built."
        ),
        "embedded_corpus_fraction": (
            round(coverage.total_embedded / coverage.total_stored, 4)
            if coverage.total_stored
            else 0.0
        ),
    }
