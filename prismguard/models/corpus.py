"""Build classifier training corpora from PrismGuard seed DB and feedback."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from prismguard.seed.bundled import BundledProfile
from prismguard.seed.models import EntrySeed, ParsedSeed
from prismguard.seed.normalize import normalize_seed_text
from prismguard.storage.protocols import StorageBackend

TrainingLabel = Literal[0, 1]


@dataclass(frozen=True)
class TrainingExample:
    text: str
    label: TrainingLabel  # 0=safe, 1=injection
    source: str = "seed"
    category_slug: str = ""


@dataclass
class TrainingCorpusManifest:
    profile: str
    total_examples: int
    injection_examples: int
    benign_examples: int
    sources: dict[str, int] = field(default_factory=dict)
    categories: dict[str, int] = field(default_factory=dict)
    fingerprint: str = ""
    built_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


def _attack_slugs(parsed: ParsedSeed) -> dict[str, bool]:
    attack: dict[str, bool] = {}
    for category in parsed.categories:
        attack[category.slug] = category.is_attack_category
    return attack


def _label_for_category(category_slug: str, attack_slugs: dict[str, bool]) -> TrainingLabel | None:
    if category_slug not in attack_slugs:
        # Staged imports without taxonomy row: treat as injection unless explicitly benign.
        if category_slug == "benign_adjacent":
            return 0
        return 1
    return 1 if attack_slugs[category_slug] else 0


def examples_from_entry(
    entry: EntrySeed,
    *,
    attack_slugs: dict[str, bool],
) -> TrainingExample | None:
    text = entry.canonical_text()
    if not text:
        return None
    label = _label_for_category(entry.category_slug, attack_slugs)
    if label is None:
        return None
    return TrainingExample(
        text=text,
        label=label,
        source=entry.source or "seed",
        category_slug=entry.category_slug,
    )


def examples_from_parsed_seed(parsed: ParsedSeed) -> list[TrainingExample]:
    attack_slugs = _attack_slugs(parsed)
    rows: list[TrainingExample] = []
    for entry in parsed.entries:
        example = examples_from_entry(entry, attack_slugs=attack_slugs)
        if example is not None:
            rows.append(example)
    return rows


def examples_from_storage(storage: StorageBackend) -> list[TrainingExample]:
    attack_slugs = {c.slug: c.is_attack_category for c in storage.relational.list_categories()}
    rows: list[TrainingExample] = []
    for category in storage.relational.list_categories():
        for record in storage.vector.list_seed_entries_by_category(category.slug):
            label = _label_for_category(record.category_slug, attack_slugs)
            if label is None:
                continue
            text = (record.raw_text or record.chunk_text or "").strip()
            if not text:
                continue
            rows.append(
                TrainingExample(
                    text=text,
                    label=label,
                    source=record.source or "storage",
                    category_slug=record.category_slug,
                )
            )
    return rows


def _read_feedback_jsonl(path: Path) -> list[TrainingExample]:
    rows: list[TrainingExample] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            text = str(payload.get("prompt") or payload.get("text") or "").strip()
            if not text:
                continue
            decision = str(payload.get("decision", "")).lower()
            if decision == "block":
                rows.append(
                    TrainingExample(
                        text=text,
                        label=1,
                        source=str(payload.get("source", "feedback")),
                        category_slug=str(payload.get("category_slug", "")),
                    )
                )
            elif decision == "allow":
                rows.append(
                    TrainingExample(
                        text=text,
                        label=0,
                        source=str(payload.get("source", "feedback")),
                        category_slug=str(payload.get("category_slug", "")),
                    )
                )
    return rows


def merge_training_examples(
    *groups: list[TrainingExample],
) -> list[TrainingExample]:
    """Deduplicate by normalized text. Conflicting labels resolve fail-closed (injection wins)."""
    merged: dict[str, TrainingExample] = {}
    for group in groups:
        for example in group:
            key = normalize_seed_text(example.text)
            if not key:
                continue
            existing = merged.get(key)
            if existing is None:
                merged[key] = example
                continue
            label: TrainingLabel = 1 if (existing.label == 1 or example.label == 1) else 0
            source = example.source if example.source != "seed" else existing.source
            merged[key] = TrainingExample(
                text=example.text,
                label=label,
                source=source,
                category_slug=example.category_slug or existing.category_slug,
            )
    return list(merged.values())


def build_training_corpus(
    *,
    parsed_seed: ParsedSeed | None = None,
    storage: StorageBackend | None = None,
    feedback_paths: list[Path] | None = None,
    profile: BundledProfile | str = "full",
) -> tuple[list[TrainingExample], TrainingCorpusManifest]:
    groups: list[list[TrainingExample]] = []
    if parsed_seed is not None:
        groups.append(examples_from_parsed_seed(parsed_seed))
    if storage is not None:
        groups.append(examples_from_storage(storage))
    for path in feedback_paths or []:
        groups.append(_read_feedback_jsonl(path))

    examples = merge_training_examples(*groups) if groups else []
    manifest = corpus_manifest(examples, profile=profile)
    return examples, manifest


def corpus_manifest(
    examples: list[TrainingExample],
    *,
    profile: BundledProfile | str,
) -> TrainingCorpusManifest:
    sources: dict[str, int] = {}
    categories: dict[str, int] = {}
    injection = 0
    benign = 0
    for example in examples:
        sources[example.source] = sources.get(example.source, 0) + 1
        if example.category_slug:
            categories[example.category_slug] = categories.get(example.category_slug, 0) + 1
        if example.label == 1:
            injection += 1
        else:
            benign += 1
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "profile": profile,
                "total": len(examples),
                "injection": injection,
                "benign": benign,
                "sources": sources,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return TrainingCorpusManifest(
        profile=str(profile),
        total_examples=len(examples),
        injection_examples=injection,
        benign_examples=benign,
        sources=sources,
        categories=categories,
        fingerprint=fingerprint,
    )


def write_corpus_manifest(path: Path, manifest: TrainingCorpusManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")


def subsample_training_examples(
    examples: list[TrainingExample],
    *,
    max_examples: int,
    seed: int = 42,
) -> list[TrainingExample]:
    """Stratified subsample for faster dev/CI runs; 0 or negative max_examples keeps all."""
    if max_examples <= 0 or len(examples) <= max_examples:
        return examples
    try:
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise RuntimeError("Subsample requires scikit-learn (prismguard[train])") from exc

    texts = [row.text for row in examples]
    labels = [row.label for row in examples]
    if len(set(labels)) < 2:
        return examples[:max_examples]
    _, selected_texts, _, selected_labels = train_test_split(
        texts,
        labels,
        test_size=max_examples,
        random_state=seed,
        stratify=labels,
    )
    text_to_example = {row.text: row for row in examples}
    return [
        text_to_example[text]
        for text in selected_texts
        if text in text_to_example
    ]
