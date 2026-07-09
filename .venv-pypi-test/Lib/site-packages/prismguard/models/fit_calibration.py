"""Fit temperature calibration on an existing HF checkpoint and write to ONNX artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prismguard.models.calibration import CalibrationArtifact, fit_temperature, write_calibration
from prismguard.models.constants import DEFAULT_MAX_LENGTH
from prismguard.models.eval import evaluate_classifier_from_config
from prismguard.models.hf_utils import load_training_model, load_training_tokenizer
from prismguard.models.loader import default_artifacts_root, resolve_artifact_dir
from prismguard.models.model_card import ModelCard, load_model_card, write_model_card
from prismguard.models.train import collect_calibration_logits, evaluate_holdout_classifier
from prismguard.config.loader import GuardModelConfig


def fit_calibration_artifact(
    *,
    base_model: str,
    artifact_id: str,
    artifact_path: str = "",
    max_length: int = DEFAULT_MAX_LENGTH,
    domain: str = "law",
    uncertain_low: float = 0.35,
    uncertain_high: float = 0.65,
) -> Path:
    artifact_dir = resolve_artifact_dir(
        GuardModelConfig(artifact_id=artifact_id, artifact_path=artifact_path)
    )
    tokenizer = load_training_tokenizer(base_model)
    model = load_training_model(base_model, num_labels=2)

    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    logits, labels = collect_calibration_logits(
        model,
        tokenizer,
        device,
        max_length=max_length,
        domain=domain,
    )
    temperature = fit_temperature(logits, labels) if len(logits) else 1.0

    holdout = evaluate_holdout_classifier(
        model,
        tokenizer,
        device,
        max_length=max_length,
        domain=domain,
        uncertain_low=uncertain_low,
        uncertain_high=uncertain_high,
    )

    write_calibration(
        artifact_dir,
        CalibrationArtifact(
            temperature=temperature,
            domain=domain,
            holdout_block_rate=holdout["holdout_block_rate"],
            normal_allow_rate=holdout["normal_allow_rate"],
        ),
    )

    card = load_model_card(artifact_dir)
    write_model_card(
        artifact_dir,
        ModelCard(
            model_id=card.model_id,
            version=card.version,
            architecture=card.architecture,
            max_length=card.max_length,
            injection_label=card.injection_label,
            base_model=card.base_model,
            description=card.description,
            calibration_temperature=temperature,
            domain=domain,
        ),
    )

    metrics_path = artifact_dir / "train_metrics.json"
    metrics: dict = {}
    if metrics_path.is_file():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["calibration_temperature"] = temperature
    metrics["holdout_block_rate_calibrated"] = holdout["holdout_block_rate"]
    metrics["normal_allow_rate_calibrated"] = holdout["normal_allow_rate"]
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return artifact_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fit temperature calibration for an ONNX artifact")
    parser.add_argument("--base-model", default="")
    parser.add_argument("--artifact-id", default="prism-pi-v1")
    parser.add_argument("--artifact-path", default="")
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--domain", default="law", choices=["law", "healthcare", "finance"])
    args = parser.parse_args(argv)

    artifact_dir = (
        Path(args.artifact_path).resolve()
        if args.artifact_path
        else default_artifacts_root() / args.artifact_id
    )
    base_model = args.base_model or str(artifact_dir.parent / f"{args.artifact_id}-hf")
    if not Path(base_model).is_dir():
        card = load_model_card(artifact_dir)
        base_model = card.base_model

    out = fit_calibration_artifact(
        base_model=base_model,
        artifact_id=args.artifact_id,
        artifact_path=args.artifact_path,
        max_length=args.max_length,
        domain=args.domain,
    )
    result = evaluate_classifier_from_config(
        domain=args.domain,  # type: ignore[arg-type]
        config=GuardModelConfig(artifact_id=args.artifact_id, artifact_path=args.artifact_path),
    )
    print(
        f"Wrote calibration to {out / 'calibration.json'} "
        f"holdout_block={result.holdout_block_rate:.1%} "
        f"normal_allow={result.normal_allow_rate:.1%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
