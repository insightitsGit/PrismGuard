"""Fine-tune and export a PrismGuard-owned prompt-injection classifier."""

from __future__ import annotations

import argparse
import copy
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from prismguard.models.calibration import (
    CalibrationArtifact,
    fit_temperature,
    write_calibration,
)
from prismguard.models.constants import DEFAULT_MAX_LENGTH
from prismguard.models.corpus import (
    TrainingCorpusManifest,
    TrainingExample,
    build_training_corpus,
    corpus_manifest,
    default_law_training_paths,
    oversample_thin_categories,
    subsample_training_examples,
    write_corpus_manifest,
)
from prismguard.models.export import export_onnx_artifact
from prismguard.models.hf_utils import load_training_model, load_training_tokenizer
from prismguard.models.loader import default_artifacts_root
from prismguard.models.verdict import injection_probability_to_decision
from prismguard.seed.bundled import BundledProfile, load_bundled_seed
from prismguard.storage import create_storage, create_storage_from_env


@dataclass(frozen=True)
class TrainOptions:
    class_weighted: bool = False
    focal_loss: bool = False
    focal_gamma: float = 2.0
    holdout_early_stop: bool = False
    holdout_domain: str = "law"
    fit_calibration: bool = True
    uncertain_low: float = 0.35
    uncertain_high: float = 0.65


def _holdout_attack_rows(domain: str) -> list[dict[str, str]]:
    from prismguard.models.eval import _holdout_rows

    return [row for row in _holdout_rows(domain) if row["traffic_kind"] == "attack"]


def _normal_rows() -> list[dict[str, str]]:
    from prismguard.models.eval import _normal_rows

    return _normal_rows()


def _injection_probability(
    model: Any,
    tokenizer: Any,
    device: Any,
    text: str,
    *,
    max_length: int,
) -> float:
    import torch

    encoded = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )
    with torch.no_grad():
        logits = model(
            input_ids=encoded["input_ids"].to(device),
            attention_mask=encoded["attention_mask"].to(device),
        ).logits
    probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
    return float(probs[1])


def evaluate_holdout_classifier(
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    max_length: int,
    domain: str = "law",
    uncertain_low: float = 0.35,
    uncertain_high: float = 0.65,
) -> dict[str, float]:
    attacks = _holdout_attack_rows(domain)
    normals = _normal_rows()
    blocked = 0
    for row in attacks:
        prob = _injection_probability(model, tokenizer, device, row["text"], max_length=max_length)
        if injection_probability_to_decision(
            prob, uncertain_low=uncertain_low, uncertain_high=uncertain_high
        ) == "block":
            blocked += 1
    allowed = 0
    for row in normals:
        prob = _injection_probability(model, tokenizer, device, row["text"], max_length=max_length)
        if injection_probability_to_decision(
            prob, uncertain_low=uncertain_low, uncertain_high=uncertain_high
        ) == "allow":
            allowed += 1
    return {
        "holdout_block_rate": blocked / len(attacks) if attacks else 0.0,
        "normal_allow_rate": allowed / len(normals) if normals else 1.0,
    }


def collect_calibration_logits(
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    max_length: int,
    domain: str = "law",
) -> tuple[np.ndarray, np.ndarray]:
    labeled_rows: list[tuple[str, int]] = []
    for row in _holdout_attack_rows(domain):
        labeled_rows.append((row["text"], 1))
    from prismguard.models.eval import _holdout_rows

    for row in _holdout_rows(domain):
        if row["traffic_kind"] == "benign_adjacent":
            labeled_rows.append((row["text"], 0))
    for row in _normal_rows():
        labeled_rows.append((row["text"], 0))

    logits_list: list[np.ndarray] = []
    labels_list: list[int] = []
    import torch

    with torch.no_grad():
        for text, label in labeled_rows:
            encoded = tokenizer(
                text,
                truncation=True,
                padding="max_length",
                max_length=max_length,
                return_tensors="pt",
            )
            logits = (
                model(
                    input_ids=encoded["input_ids"].to(device),
                    attention_mask=encoded["attention_mask"].to(device),
                )
                .logits.cpu()
                .numpy()[0]
            )
            logits_list.append(logits)
            labels_list.append(label)
    return np.asarray(logits_list, dtype=np.float64), np.asarray(labels_list, dtype=np.int64)


def _build_loss_fn(
    *,
    train_labels: list[int],
    device: Any,
    options: TrainOptions,
) -> Any:
    import torch
    import torch.nn.functional as F
    from sklearn.utils.class_weight import compute_class_weight

    weight_tensor = None
    if options.class_weighted:
        weights = compute_class_weight(
            class_weight="balanced",
            classes=np.array([0, 1]),
            y=np.array(train_labels),
        )
        weight_tensor = torch.tensor(weights, dtype=torch.float32, device=device)

    if options.focal_loss:

        class FocalLoss(torch.nn.Module):
            def __init__(self, gamma: float, weight: Any) -> None:
                super().__init__()
                self.gamma = gamma
                self.weight = weight

            def forward(self, logits: Any, targets: Any) -> Any:
                ce = F.cross_entropy(logits, targets, weight=self.weight, reduction="none")
                pt = torch.exp(-ce)
                return (((1 - pt) ** self.gamma) * ce).mean()

        return FocalLoss(options.focal_gamma, weight_tensor)

    return torch.nn.CrossEntropyLoss(weight=weight_tensor)


def train_and_export(
    *,
    base_model: str,
    artifact_id: str,
    examples: list[TrainingExample],
    manifest: TrainingCorpusManifest,
    output_dir: Path | None = None,
    epochs: int = 1,
    batch_size: int = 8,
    learning_rate: float = 2e-5,
    max_length: int = DEFAULT_MAX_LENGTH,
    eval_split: float = 0.1,
    seed: int = 42,
    options: TrainOptions | None = None,
) -> Path:
    if not examples:
        raise ValueError("Training corpus is empty")

    opts = options or TrainOptions()

    try:
        import torch
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import train_test_split
        from torch.utils.data import DataLoader, Dataset
        from transformers import get_linear_schedule_with_warmup
    except ImportError as exc:
        raise RuntimeError(
            "Training requires extras: pip install -e '.[train]'"
        ) from exc

    texts = [row.text for row in examples]
    labels = [row.label for row in examples]
    train_texts, eval_texts, train_labels, eval_labels = train_test_split(
        texts,
        labels,
        test_size=eval_split,
        random_state=seed,
        stratify=labels if len(set(labels)) > 1 else None,
    )

    tokenizer = load_training_tokenizer(base_model)
    model = load_training_model(base_model, num_labels=2)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    loss_fn = _build_loss_fn(train_labels=train_labels, device=device, options=opts)

    class _PromptDataset(Dataset):
        def __init__(self, items: list[tuple[str, int]]) -> None:
            self._items = items

        def __len__(self) -> int:
            return len(self._items)

        def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
            text, label = self._items[index]
            encoded = tokenizer(
                text,
                truncation=True,
                padding="max_length",
                max_length=max_length,
                return_tensors="pt",
            )
            return {
                "input_ids": encoded["input_ids"].squeeze(0),
                "attention_mask": encoded["attention_mask"].squeeze(0),
                "labels": torch.tensor(label, dtype=torch.long),
            }

    train_loader = DataLoader(
        _PromptDataset(list(zip(train_texts, train_labels, strict=True))),
        batch_size=batch_size,
        shuffle=True,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    total_steps = max(1, len(train_loader) * epochs)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, total_steps // 10),
        num_training_steps=total_steps,
    )

    best_score = -1.0
    best_state: dict[str, Any] | None = None
    model.train()
    total_batches = len(train_loader) * epochs
    batch_num = 0
    for epoch in range(epochs):
        for batch in train_loader:
            batch_num += 1
            if batch_num == 1 or batch_num % 100 == 0 or batch_num == total_batches:
                print(f"Training batch {batch_num}/{total_batches} (epoch {epoch + 1}/{epochs})")
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels_tensor = batch["labels"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = loss_fn(outputs.logits, labels_tensor)
            loss.backward()
            optimizer.step()
            scheduler.step()

        if opts.holdout_early_stop:
            model.eval()
            holdout = evaluate_holdout_classifier(
                model,
                tokenizer,
                device,
                max_length=max_length,
                domain=opts.holdout_domain,
                uncertain_low=opts.uncertain_low,
                uncertain_high=opts.uncertain_high,
            )
            score = (
                holdout["holdout_block_rate"]
                if holdout["normal_allow_rate"] >= 1.0
                else 0.0
            )
            print(
                f"Holdout epoch {epoch + 1}: block={holdout['holdout_block_rate']:.1%} "
                f"normal_allow={holdout['normal_allow_rate']:.1%}"
            )
            if score > best_score:
                best_score = score
                best_state = copy.deepcopy(model.state_dict())
            model.train()

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    eval_preds: list[int] = []
    eval_true: list[int] = []
    with torch.no_grad():
        for text, label in zip(eval_texts, eval_labels, strict=True):
            encoded = tokenizer(
                text,
                truncation=True,
                padding="max_length",
                max_length=max_length,
                return_tensors="pt",
            )
            logits = model(
                input_ids=encoded["input_ids"].to(device),
                attention_mask=encoded["attention_mask"].to(device),
            ).logits
            pred = int(torch.argmax(logits, dim=-1).item())
            eval_preds.append(pred)
            eval_true.append(int(label))

    holdout_metrics = evaluate_holdout_classifier(
        model,
        tokenizer,
        device,
        max_length=max_length,
        domain=opts.holdout_domain,
        uncertain_low=opts.uncertain_low,
        uncertain_high=opts.uncertain_high,
    )

    metrics = {
        "artifact_id": artifact_id,
        "trained_at": datetime.now(UTC).isoformat(),
        "accuracy": float(accuracy_score(eval_true, eval_preds)),
        "f1_injection": float(f1_score(eval_true, eval_preds, pos_label=1, zero_division=0)),
        "train_size": len(train_texts),
        "eval_size": len(eval_texts),
        "base_model": base_model,
        "max_length": max_length,
        "corpus": manifest.to_dict(),
        "holdout_block_rate": holdout_metrics["holdout_block_rate"],
        "normal_allow_rate": holdout_metrics["normal_allow_rate"],
        "train_options": {
            "class_weighted": opts.class_weighted,
            "focal_loss": opts.focal_loss,
            "holdout_early_stop": opts.holdout_early_stop,
        },
    }

    artifact_root = output_dir or (default_artifacts_root() / artifact_id)
    work_dir = artifact_root.parent / f"{artifact_id}-hf"
    work_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(work_dir)
    tokenizer.save_pretrained(work_dir)
    (work_dir / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    calibration_temperature = 1.0
    if opts.fit_calibration:
        logits, cal_labels = collect_calibration_logits(
            model,
            tokenizer,
            device,
            max_length=max_length,
            domain=opts.holdout_domain,
        )
        if len(logits) > 0:
            calibration_temperature = fit_temperature(logits, cal_labels)
            holdout_after = evaluate_holdout_classifier(
                model,
                tokenizer,
                device,
                max_length=max_length,
                domain=opts.holdout_domain,
                uncertain_low=opts.uncertain_low,
                uncertain_high=opts.uncertain_high,
            )
            metrics["calibration_temperature"] = calibration_temperature
            metrics["holdout_block_rate_calibrated"] = holdout_after["holdout_block_rate"]
            (work_dir / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    artifact_dir = export_onnx_artifact(
        base_model=str(work_dir),
        artifact_id=artifact_id,
        output_dir=artifact_root,
        max_length=max_length,
    )
    write_corpus_manifest(artifact_dir / "corpus_manifest.json", manifest)
    if not (artifact_dir / "train_metrics.json").is_file():
        (artifact_dir / "train_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    if opts.fit_calibration and calibration_temperature != 1.0:
        write_calibration(
            artifact_dir,
            CalibrationArtifact(
                temperature=calibration_temperature,
                domain=opts.holdout_domain,
                holdout_block_rate=holdout_metrics["holdout_block_rate"],
                normal_allow_rate=holdout_metrics["normal_allow_rate"],
            ),
        )
        from prismguard.models.model_card import ModelCard, load_model_card, write_model_card

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
                calibration_temperature=calibration_temperature,
                domain=opts.holdout_domain,
            ),
        )

    return artifact_dir


def load_corpus_for_training(
    *,
    profile: BundledProfile = "full",
    feedback_paths: list[Path] | None = None,
    seed_yaml_paths: list[Path] | None = None,
    from_storage: bool = False,
    storage_backend: str = "",
    oversample_law: bool = False,
) -> tuple[list[TrainingExample], TrainingCorpusManifest]:
    import logging

    logging.getLogger("prismguard.seed.merge").setLevel(logging.WARNING)
    parsed = load_bundled_seed(profile=profile)
    storage = None
    if from_storage:
        storage = (
            create_storage(storage_backend)
            if storage_backend
            else create_storage_from_env()
            if os.environ.get("PRISMGUARD_STORAGE_BACKEND") or os.environ.get("PRISMGUARD_STORAGE_DSN")
            else None
        )
    examples, manifest = build_training_corpus(
        parsed_seed=parsed,
        storage=storage,
        feedback_paths=feedback_paths,
        seed_yaml_paths=seed_yaml_paths,
        profile=profile,
    )
    if oversample_law:
        examples = oversample_thin_categories(examples)
        manifest = corpus_manifest(examples, profile=str(profile))
    return examples, manifest


def print_corpus_stats(
    *,
    profile: BundledProfile = "full",
    feedback_paths: list[Path] | None = None,
    seed_yaml_paths: list[Path] | None = None,
    from_storage: bool = False,
    storage_backend: str = "",
    oversample_law: bool = False,
) -> TrainingCorpusManifest:
    _, manifest = load_corpus_for_training(
        profile=profile,
        feedback_paths=feedback_paths,
        seed_yaml_paths=seed_yaml_paths,
        from_storage=from_storage,
        storage_backend=storage_backend,
        oversample_law=oversample_law,
    )
    print(json.dumps(manifest.to_dict(), indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train PrismGuard prompt-injection classifier")
    parser.add_argument(
        "--base-model",
        default="ProtectAI/deberta-v3-base-prompt-injection",
        help="HuggingFace checkpoint or path to a prior prism-pi-*-hf directory for incremental training",
    )
    parser.add_argument("--artifact-id", default="prism-pi-v1")
    parser.add_argument("--profile", default="full", choices=["authored", "full"])
    parser.add_argument("--from-storage", action="store_true", help="Merge live storage seed rows (pgvector/memory)")
    parser.add_argument("--storage-backend", default="", help="memory | pgvector | ... when using --from-storage")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument(
        "--max-train-examples",
        type=int,
        default=0,
        help="Stratified cap on training rows (0 = use full corpus). Useful on CPU.",
    )
    parser.add_argument(
        "--feedback-jsonl",
        action="append",
        default=[],
        help="Reviewed feedback export (repeatable). May be passed multiple times.",
    )
    parser.add_argument(
        "--seed-yaml",
        action="append",
        default=[],
        help="Extra labeled seed YAML (e.g. law overlay). Repeatable.",
    )
    parser.add_argument(
        "--law-pack",
        action="store_true",
        help="Include law overlay YAML + augment/hard-negative JSONL (never holdout).",
    )
    parser.add_argument("--oversample-law", action="store_true", help="Oversample thin attack categories")
    parser.add_argument("--class-weighted", action="store_true", help="Balanced class weights in loss")
    parser.add_argument("--focal-loss", action="store_true", help="Focal loss for rare attack types")
    parser.add_argument("--holdout-early-stop", action="store_true", help="Checkpoint best holdout epoch")
    parser.add_argument("--holdout-domain", default="law", choices=["law", "healthcare", "finance"])
    parser.add_argument("--no-calibration", action="store_true", help="Skip temperature scaling artifact")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args(argv)

    feedback_paths = [Path(p) for p in args.feedback_jsonl]
    seed_yaml_paths = [Path(p) for p in args.seed_yaml]
    if args.law_pack:
        law_seed, law_feedback = default_law_training_paths()
        seed_yaml_paths.extend(law_seed)
        feedback_paths.extend(law_feedback)

    examples, manifest = load_corpus_for_training(
        profile=args.profile,  # type: ignore[arg-type]
        feedback_paths=feedback_paths,
        seed_yaml_paths=seed_yaml_paths,
        from_storage=args.from_storage,
        storage_backend=args.storage_backend,
        oversample_law=args.oversample_law,
    )
    if not examples:
        raise SystemExit("Training corpus is empty — import seed or pass --feedback-jsonl")

    if args.max_train_examples > 0:
        examples = subsample_training_examples(examples, max_examples=args.max_train_examples)
        manifest = corpus_manifest(examples, profile=str(args.profile))
        print(f"Subsampled to {len(examples)} examples for this run")

    options = TrainOptions(
        class_weighted=args.class_weighted,
        focal_loss=args.focal_loss,
        holdout_early_stop=args.holdout_early_stop,
        holdout_domain=args.holdout_domain,
        fit_calibration=not args.no_calibration,
    )

    output = Path(args.output_dir) if args.output_dir else None
    artifact_dir = train_and_export(
        base_model=args.base_model,
        artifact_id=args.artifact_id,
        examples=examples,
        manifest=manifest,
        output_dir=output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_length=args.max_length,
        options=options,
    )
    print(f"Trained and exported artifact to {artifact_dir}")
    print(f"Corpus fingerprint: {manifest.fingerprint} ({manifest.total_examples} examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
