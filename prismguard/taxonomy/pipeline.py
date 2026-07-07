from __future__ import annotations

from dataclasses import dataclass, field

from prismguard.seed.models import ParsedSeed
from prismguard.storage.protocols import StorageBackend
from prismguard.taxonomy.embedder import Embedder, create_embedder
from prismguard.taxonomy.ingest import IngestReport, ingest_seed_vectors, iter_all_seed_entries
from prismguard.taxonomy.mapping import TaxonomyEngine, build_mapping_after_import, build_mapping_from_parsed_seed
from prismguard.taxonomy.report import CoverageReport, build_coverage_report, estimate_llm_reduction


@dataclass
class PostSeedReport:
    ingest: IngestReport
    coverage: CoverageReport
    llm_reduction: dict[str, float | str]
    engine: TaxonomyEngine
    embedder_name: str


def run_post_seed_pipeline(
    storage: StorageBackend,
    parsed: ParsedSeed,
    *,
    force_embed: bool = False,
    embedder: Embedder | None = None,
) -> PostSeedReport:
    """Run prismRAG taxonomy wiring + dual-vector ingest immediately after seed import."""
    engine = build_mapping_after_import(storage, parsed)
    emb = embedder or create_embedder(prefer_transformer=False)
    ingest_report = ingest_seed_vectors(storage, engine, emb, force=force_embed)
    coverage = build_coverage_report(storage, parsed, engine)
    reduction = estimate_llm_reduction(coverage)
    return PostSeedReport(
        ingest=ingest_report,
        coverage=coverage,
        llm_reduction=reduction,
        engine=engine,
        embedder_name=type(emb).__name__,
    )
