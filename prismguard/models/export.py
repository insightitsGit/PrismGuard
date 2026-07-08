"""Export a HuggingFace sequence-classification model to PrismGuard ONNX artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from prismguard.models.constants import DEFAULT_MAX_LENGTH
from prismguard.models.hf_utils import load_training_model, load_training_tokenizer
from prismguard.models.loader import default_artifacts_root
from prismguard.models.model_card import ModelCard, write_model_card


def _copy_tokenizer_files(source_dir: Path, artifact_dir: Path) -> None:
    for name in (
        "tokenizer.json",
        "tokenizer_config.json",
        "spm.model",
        "special_tokens_map.json",
        "added_tokens.json",
    ):
        src = source_dir / name
        if src.is_file():
            shutil.copy2(src, artifact_dir / name)


def export_onnx_artifact(
    *,
    base_model: str,
    artifact_id: str,
    output_dir: Path | None = None,
    max_length: int = DEFAULT_MAX_LENGTH,
) -> Path:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Export requires training extras: pip install -e '.[train]'"
        ) from exc

    artifact_dir = output_dir or (default_artifacts_root() / artifact_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = artifact_dir / "model.onnx"
    source_dir = Path(base_model)

    model = load_training_model(base_model, num_labels=2)
    tokenizer = load_training_tokenizer(base_model)
    model.eval()

    encoded = tokenizer(
        "export calibration prompt",
        return_tensors="pt",
        max_length=max_length,
        truncation=True,
        padding="max_length",
    )
    input_ids = encoded["input_ids"]
    attention_mask = encoded["attention_mask"]

    export_args = (
        model,
        (input_ids, attention_mask),
        str(onnx_path),
    )
    export_kwargs = {
        "input_names": ["input_ids", "attention_mask"],
        "output_names": ["logits"],
        "dynamic_axes": {
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "logits": {0: "batch"},
        },
        "opset_version": 14,
    }
    try:
        torch.onnx.export(*export_args, **export_kwargs, dynamo=False)
    except TypeError:
        torch.onnx.export(*export_args, **export_kwargs)

    if source_dir.is_dir():
        _copy_tokenizer_files(source_dir, artifact_dir)
        metrics_path = source_dir / "train_metrics.json"
        if metrics_path.is_file():
            shutil.copy2(metrics_path, artifact_dir / "train_metrics.json")
    else:
        tokenizer.save_pretrained(artifact_dir)

    description = f"Exported from {base_model}"
    metrics_file = artifact_dir / "train_metrics.json"
    if metrics_file.is_file():
        metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
        description = (
            f"Seed-trained {artifact_id}; eval accuracy={metrics.get('accuracy')}, "
            f"f1_injection={metrics.get('f1_injection')}"
        )

    card = ModelCard(
        model_id=artifact_id,
        version="1",
        architecture="sequence_classification",
        max_length=max_length,
        injection_label=1,
        base_model=base_model,
        description=description,
    )
    write_model_card(artifact_dir, card)
    return artifact_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export PrismGuard Guard Model ONNX artifact")
    parser.add_argument(
        "--base-model",
        default="ProtectAI/deberta-v3-base-prompt-injection",
        help="HuggingFace model id to export",
    )
    parser.add_argument(
        "--artifact-id",
        default="prism-pi-v1",
        help="Artifact directory name under prismguard/models/artifacts/",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Override output directory (default: packaged artifacts/<artifact-id>)",
    )
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    args = parser.parse_args(argv)

    output = Path(args.output_dir) if args.output_dir else None
    artifact_dir = export_onnx_artifact(
        base_model=args.base_model,
        artifact_id=args.artifact_id,
        output_dir=output,
        max_length=args.max_length,
    )
    print(f"Exported ONNX artifact to {artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
