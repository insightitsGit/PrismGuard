"""Fine-tune and export a PrismGuard-owned prompt-injection classifier."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from prismguard.models.corpus import (
    TrainingCorpusManifest,
    TrainingExample,
    build_training_corpus,
    corpus_manifest,
    subsample_training_examples,
    write_corpus_manifest,
)
from prismguard.models.export import export_onnx_artifact
from prismguard.models.hf_utils import load_training_model, load_training_tokenizer
from prismguard.models.loader import default_artifacts_root
from prismguard.seed.bundled import BundledProfile, load_bundled_seed
from prismguard.storage import create_storage, create_storage_from_env


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
    max_length: int = 256,
    eval_split: float = 0.1,
    seed: int = 42,
) -> Path:
    if not examples:
        raise ValueError("Training corpus is empty")

    try:
        import torch
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import train_test_split
        from torch.utils.data import DataLoader, Dataset
        from transformers import AutoModelForSequenceClassification, get_linear_schedule_with_warmup
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
    loss_fn = torch.nn.CrossEntropyLoss()

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

    metrics = {
        "artifact_id": artifact_id,
        "trained_at": datetime.now(UTC).isoformat(),
        "accuracy": float(accuracy_score(eval_true, eval_preds)),
        "f1_injection": float(f1_score(eval_true, eval_preds, pos_label=1, zero_division=0)),
        "train_size": len(train_texts),
        "eval_size": len(eval_texts),
        "base_model": base_model,
        "corpus": manifest.to_dict(),
    }

    artifact_root = output_dir or (default_artifacts_root() / artifact_id)
    work_dir = artifact_root.parent / f"{artifact_id}-hf"
    work_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(work_dir)
    tokenizer.save_pretrained(work_dir)
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
    return artifact_dir


def load_corpus_for_training(
    *,
    profile: BundledProfile = "full",
    feedback_paths: list[Path] | None = None,
    from_storage: bool = False,
    storage_backend: str = "",
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
    return build_training_corpus(
        parsed_seed=parsed,
        storage=storage,
        feedback_paths=feedback_paths,
        profile=profile,
    )


def print_corpus_stats(
    *,
    profile: BundledProfile = "full",
    feedback_paths: list[Path] | None = None,
    from_storage: bool = False,
    storage_backend: str = "",
) -> TrainingCorpusManifest:
    _, manifest = load_corpus_for_training(
        profile=profile,
        feedback_paths=feedback_paths,
        from_storage=from_storage,
        storage_backend=storage_backend,
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
    parser.add_argument("--max-length", type=int, default=256)
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
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args(argv)

    feedback_paths = [Path(p) for p in args.feedback_jsonl]
    examples, manifest = load_corpus_for_training(
        profile=args.profile,  # type: ignore[arg-type]
        feedback_paths=feedback_paths,
        from_storage=args.from_storage,
        storage_backend=args.storage_backend,
    )
    if not examples:
        raise SystemExit("Training corpus is empty — import seed or pass --feedback-jsonl")

    if args.max_train_examples > 0:
        examples = subsample_training_examples(examples, max_examples=args.max_train_examples)
        manifest = corpus_manifest(examples, profile=str(args.profile))
        print(f"Subsampled to {len(examples)} examples for this run")

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
    )
    print(f"Trained and exported artifact to {artifact_dir}")
    print(f"Corpus fingerprint: {manifest.fingerprint} ({manifest.total_examples} examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
