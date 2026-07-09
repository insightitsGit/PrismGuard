from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from prismguard.config.loader import TriageConfig, load_triage_config
from prismguard.runtime.check import RuntimeChecker
from prismguard.seed import load_bundled_seed
from prismguard.storage import create_storage


@dataclass(frozen=True)
class TuneResult:
    block_threshold: float
    allow_threshold: float
    w_clf: float
    holdout_block_rate: float
    normal_allow_rate: float
    score: float


def _holdout_rows(domain: str = "law") -> list[dict[str, str]]:
    from prismguard.domains.registry import get_domain_pack

    pack = get_domain_pack(domain)
    holdout_path = pack.holdout_path
    if holdout_path is None or not holdout_path.is_file():
        return []
    with holdout_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    rows: list[dict[str, str]] = []
    for entry in raw.get("entries") or []:
        slug = entry.get("category_slug", "")
        kind = "attack" if slug != "benign_adjacent" else "benign_adjacent"
        rows.append({"text": entry["text"], "traffic_kind": kind, "category_slug": slug})
    return rows


def _normal_rows() -> list[dict[str, str]]:
    from benchmark.law.shared.normal_scenarios import load_normal_scenarios

    return [
        {"text": s.text, "traffic_kind": "normal", "category_slug": s.category_hint}
        for s in load_normal_scenarios()
    ]


def _evaluate_config(
    checker: RuntimeChecker,
    cfg: TriageConfig,
    rows: list[dict[str, str]],
) -> tuple[float, float]:
    """Return (attack_block_rate, normal_allow_rate) for holdout + normal rows."""
    attacks = [r for r in rows if r["traffic_kind"] == "attack"]
    normals = [r for r in rows if r["traffic_kind"] == "normal"]
    blocked = 0
    for row in attacks:
        result = checker.check(row["text"])
        if result.decision == "block":
            blocked += 1
    attack_rate = blocked / len(attacks) if attacks else 0.0
    allowed = 0
    for row in normals:
        result = checker.check(row["text"])
        if result.decision == "allow":
            allowed += 1
    normal_rate = allowed / len(normals) if normals else 1.0
    return attack_rate, normal_rate


def tune_thresholds(
    *,
    domain: str = "law",
    block_grid: list[float] | None = None,
    allow_grid: list[float] | None = None,
    w_clf_grid: list[float] | None = None,
    config_path: Path | None = None,
) -> TuneResult:
    block_grid = block_grid or [0.68, 0.72, 0.76, 0.78]
    allow_grid = allow_grid or [0.38, 0.42, 0.46]
    w_clf_grid = w_clf_grid or [0.25, 0.30, 0.35, 0.40]

    base_cfg = load_triage_config(config_path, domain=domain)
    base_cfg = base_cfg.model_copy(deep=True)
    base_cfg.embedding.prefer_transformer = False
    base_cfg.embedding.corpus_path_enabled = True  # fusion tuning requires ANN path (HashEmbedder when prefer_transformer=False)
    base_cfg.guard_model.enabled = False
    base_cfg.gray_zone_policy = "fail_closed"
    base_cfg.guard_model = base_cfg.guard_model.model_copy(update={"classifier_mode": "gray_only"})
    storage = create_storage("memory")
    parsed = load_bundled_seed(profile="authored")
    checker = RuntimeChecker.from_storage(storage, parsed, config=base_cfg)
    rows = _holdout_rows(domain) + _normal_rows()

    best: TuneResult | None = None
    for block_t in block_grid:
        for allow_t in allow_grid:
            for w_clf in w_clf_grid:
                checker._config.triage.block_threshold = block_t  # noqa: SLF001
                checker._config.triage.allow_threshold = allow_t  # noqa: SLF001
                checker._config.fusion.w_clf = w_clf  # noqa: SLF001
                attack_rate, normal_rate = _evaluate_config(checker, checker._config, rows)
                if normal_rate < 1.0:
                    continue
                score = attack_rate
                candidate = TuneResult(
                    block_threshold=block_t,
                    allow_threshold=allow_t,
                    w_clf=w_clf,
                    holdout_block_rate=round(attack_rate, 4),
                    normal_allow_rate=round(normal_rate, 4),
                    score=round(score, 4),
                )
                if best is None or candidate.score > best.score:
                    best = candidate
    storage.close()
    if best is None:
        raise RuntimeError("No threshold configuration satisfied normal-scenario pass constraint")
    return best


def write_tuned_config(result: TuneResult, output_path: Path, *, base_path: Path | None = None) -> None:
    from prismguard.config.loader import _default_config_path

    source = base_path or _default_config_path()
    base = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(base, dict):
        base = {}
    base.setdefault("triage", {})
    base["triage"]["block_threshold"] = result.block_threshold
    base["triage"]["allow_threshold"] = result.allow_threshold
    base.setdefault("fusion", {})
    base["fusion"]["w_clf"] = result.w_clf
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(base, sort_keys=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="prismguard-calibrate", description="Holdout-safe threshold tuning")
    parser.add_argument("--domain", default="law", choices=["law", "healthcare", "finance"])
    parser.add_argument("--output", type=Path, default=Path("triage.tuned.yaml"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = tune_thresholds(domain=args.domain)
    write_tuned_config(result, args.output)
    payload = {
        "block_threshold": result.block_threshold,
        "allow_threshold": result.allow_threshold,
        "w_clf": result.w_clf,
        "holdout_block_rate": result.holdout_block_rate,
        "normal_allow_rate": result.normal_allow_rate,
        "output": str(args.output),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
