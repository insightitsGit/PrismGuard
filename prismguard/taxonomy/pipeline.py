from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from prismguard.storage.protocols import StorageBackend
from prismguard.taxonomy.embedder import Embedder, create_embedder_from_config
from prismguard.taxonomy.ingest import IngestReport, ingest_seed_vectors
from prismguard.taxonomy.mapping import TaxonomyEngine, build_mapping_after_import
from prismguard.taxonomy.report import CoverageReport, build_coverage_report, estimate_llm_reduction

if TYPE_CHECKING:
    from prismguard.seed.models import ParsedSeed


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
    config=None,
) -> PostSeedReport:
    """Run prismRAG taxonomy wiring + dual-vector ingest immediately after seed import.

    Respects caller ``config`` / ``embedder``. When corpus path is disabled, offline mode
    is set, or transformers are not preferred, uses HashEmbedder (no HF Hub).
    """
    import os

    from prismguard.config.loader import load_triage_config
    from prismguard.taxonomy.embedder import HashEmbedder

    cfg = config or load_triage_config()
    offline = os.environ.get("PRISMGUARD_OFFLINE", "").strip().lower() in ("1", "true", "yes")
    prefer_transformer = bool(getattr(cfg.embedding, "prefer_transformer", False))
    corpus_on = bool(getattr(cfg.embedding, "corpus_path_enabled", False))

    if embedder is not None:
        emb = embedder
    elif offline or not corpus_on or not prefer_transformer:
        emb = HashEmbedder()
    else:
        emb = create_embedder_from_config(cfg)

    engine = build_mapping_after_import(storage, parsed)
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
