"""Classifier-only evaluation (library KPI, separate from full pipeline benchmark)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from prismguard.config.loader import GuardModelConfig, load_triage_config
from prismguard.models.loader import load_corpus_manifest
from prismguard.runtime.guard_model import GuardModel, create_guard_model

DomainName = Literal["law", "healthcare", "finance"]


@dataclass(frozen=True)
class ClassifierEvalResult:
    domain: str
    model_id: str
    holdout_block_rate: float
    holdout_blocked: int
    holdout_total: int
    normal_allow_rate: float
    normal_allowed: int
    normal_total: int
    normal_non_block_rate: float = 0.0
    normal_non_blocked: int = 0
    corpus_fingerprint: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _holdout_rows(domain: str) -> list[dict[str, str]]:
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


def evaluate_classifier(
    guard_model: GuardModel,
    *,
    domain: str = "law",
    artifact_dir: Path | None = None,
) -> ClassifierEvalResult:
    attacks = [r for r in _holdout_rows(domain) if r["traffic_kind"] == "attack"]
    normals = _normal_rows()
    blocked = 0
    per_attack: list[dict[str, Any]] = []
    for row in attacks:
        verdict = guard_model.check(row["text"])
        if verdict.decision == "block":
            blocked += 1
        per_attack.append(
            {
                "text": row["text"][:120],
                "decision": verdict.decision,
                "injection_probability": verdict.injection_probability,
                "category_slug": row["category_slug"],
            }
        )
    allowed = 0
    non_blocked = 0
    for row in normals:
        verdict = guard_model.check(row["text"])
        if verdict.decision == "allow":
            allowed += 1
        if verdict.decision != "block":
            non_blocked += 1
    fingerprint = None
    if artifact_dir is not None:
        manifest = load_corpus_manifest(artifact_dir)
        if manifest is not None:
            fingerprint = manifest.get("fingerprint")
    return ClassifierEvalResult(
        domain=domain,
        model_id=guard_model.model_id,
        holdout_block_rate=round(blocked / len(attacks), 4) if attacks else 0.0,
        holdout_blocked=blocked,
        holdout_total=len(attacks),
        normal_allow_rate=round(allowed / len(normals), 4) if normals else 1.0,
        normal_allowed=allowed,
        normal_total=len(normals),
        normal_non_block_rate=round(non_blocked / len(normals), 4) if normals else 1.0,
        normal_non_blocked=non_blocked,
        corpus_fingerprint=fingerprint,
        details={"holdout_rows": per_attack},
    )


def evaluate_classifier_from_config(
    *,
    domain: DomainName = "law",
    config: GuardModelConfig | None = None,
) -> ClassifierEvalResult:
    triage = load_triage_config(domain=domain)
    gm_cfg = config or triage.guard_model
    guard_model = create_guard_model(gm_cfg)
    if guard_model is None or not guard_model.is_ready:
        raise RuntimeError(
            f"Guard model artifact not ready for domain={domain!r} "
            f"(artifact_id={gm_cfg.artifact_id!r})"
        )
    from prismguard.models.loader import resolve_artifact_dir

    artifact_dir = resolve_artifact_dir(gm_cfg)
    return evaluate_classifier(guard_model, domain=domain, artifact_dir=artifact_dir)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Classifier-only holdout evaluation")
    parser.add_argument("--domain", default="law", choices=["law", "healthcare", "finance"])
    parser.add_argument("--artifact-id", default="")
    parser.add_argument("--artifact-path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    triage = load_triage_config(domain=args.domain)
    gm_cfg = triage.guard_model.model_copy()
    if args.artifact_id:
        gm_cfg = gm_cfg.model_copy(update={"artifact_id": args.artifact_id})
    if args.artifact_path:
        gm_cfg = gm_cfg.model_copy(update={"artifact_path": args.artifact_path})
    result = evaluate_classifier_from_config(domain=args.domain, config=gm_cfg)  # type: ignore[arg-type]
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"domain={result.domain} model={result.model_id} "
            f"holdout_block={result.holdout_blocked}/{result.holdout_total} "
            f"({result.holdout_block_rate:.1%}) "
            f"normal_allow={result.normal_allowed}/{result.normal_total} "
            f"({result.normal_allow_rate:.1%}) "
            f"normal_non_block={result.normal_non_blocked}/{result.normal_total} "
            f"({result.normal_non_block_rate:.1%})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
