"""Fusion stub ablation on held-out legal attacks (Bug3 T6)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from prismguard.config.loader import FusionConfig, TriageConfig
from prismguard.runtime.check import RuntimeChecker
from prismguard.runtime.fusion import fuse_signals
from prismguard.seed import import_bundled_seed, load_bundled_seed
from prismguard.storage import create_storage
from prismguard.taxonomy.embedder import HashEmbedder
from prismguard.taxonomy.mapping import build_mapping_from_parsed_seed

_HOLDOUT = Path(__file__).resolve().parent / "data" / "legal_attacks_holdout.yaml"


def _holdout_texts() -> list[str]:
    with _HOLDOUT.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [row["text"] for row in raw.get("entries", []) if row.get("category_slug") != "benign_adjacent"]


def run_ablation() -> dict:
    texts = _holdout_texts()
    storage = create_storage("memory")
    parsed = load_bundled_seed(profile="authored")
    import_bundled_seed(storage, profile="authored")
    engine = build_mapping_from_parsed_seed(parsed)
    embedder = HashEmbedder()

    def block_rate(*, w_graph: float, w_comm: float) -> float:
        cfg = TriageConfig(
            gray_zone_policy="fail_closed",
            fusion=FusionConfig(w_graph=w_graph, w_comm=w_comm),
        )
        checker = RuntimeChecker(storage, engine, embedder=embedder, config=cfg)
        blocked = 0
        for text in texts:
            if checker.check(text).decision == "block":
                blocked += 1
        return round(blocked / len(texts), 4) if texts else 0.0

    with_stubs = block_rate(w_graph=0.25, w_comm=0.10)
    without_stubs = block_rate(w_graph=0.0, w_comm=0.0)
    return {
        "holdout_n": len(texts),
        "block_rate_with_stub_weights": with_stubs,
        "block_rate_without_stub_weights": without_stubs,
        "decision": "zero_stub_weights",
        "rationale": "Stub graph/community terms zeroed in triage.yaml; marginal holdout delta measured here.",
    }


def main() -> None:
    out_dir = Path("benchmark/law/results/corpus_scale")
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_ablation()
    (out_dir / "fusion_ablation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
