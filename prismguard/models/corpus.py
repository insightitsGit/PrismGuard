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
from prismguard.models.constants import THIN_ATTACK_CATEGORIES
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


def examples_from_yaml_seed(path: Path) -> list[TrainingExample]:
    from prismguard.seed.parse import parse_seed_file

    parsed = parse_seed_file(path)
    return examples_from_parsed_seed(parsed)


def build_training_corpus(
    *,
    parsed_seed: ParsedSeed | None = None,
    storage: StorageBackend | None = None,
    feedback_paths: list[Path] | None = None,
    seed_yaml_paths: list[Path] | None = None,
    profile: BundledProfile | str = "full",
) -> tuple[list[TrainingExample], TrainingCorpusManifest]:
    groups: list[list[TrainingExample]] = []
    if parsed_seed is not None:
        groups.append(examples_from_parsed_seed(parsed_seed))
    if storage is not None:
        groups.append(examples_from_storage(storage))
    for path in feedback_paths or []:
        groups.append(_read_feedback_jsonl(path))
    for path in seed_yaml_paths or []:
        groups.append(examples_from_yaml_seed(path))

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


def oversample_thin_categories(
    examples: list[TrainingExample],
    *,
    min_count: int = 80,
    thin_categories: tuple[str, ...] = THIN_ATTACK_CATEGORIES,
    seed: int = 42,
) -> list[TrainingExample]:
    """Duplicate under-represented attack categories so rare law patterns get more gradient."""
    import random

    counts: dict[str, int] = {}
    for example in examples:
        if example.label != 1 or not example.category_slug:
            continue
        counts[example.category_slug] = counts.get(example.category_slug, 0) + 1

    rng = random.Random(seed)
    extra: list[TrainingExample] = []
    for category in thin_categories:
        current = counts.get(category, 0)
        if current >= min_count:
            continue
        pool = [row for row in examples if row.label == 1 and row.category_slug == category]
        if not pool:
            continue
        for _ in range(min_count - current):
            pick = pool[rng.randrange(len(pool))]
            extra.append(
                TrainingExample(
                    text=pick.text,
                    label=1,
                    source=f"{pick.source}+oversample",
                    category_slug=category,
                )
            )
    return examples + extra


def default_law_training_paths() -> tuple[list[Path], list[Path]]:
    """Law overlay YAML + augment/hard-negative JSONL (never holdout)."""
    return default_domain_training_paths("law")


def default_domain_training_paths(domain: str) -> tuple[list[Path], list[Path]]:
    """
    Domain pack overlay + optional benchmark/<domain>/data augment files.

    Opt-in via ``--domain-pack`` / ``--law-pack``. Default train uses bundled seed only.
    Never includes holdout YAML.
    """
    key = domain.strip().lower()
    seed_yaml: list[Path] = []
    feedback_jsonl: list[Path] = []

    try:
        from prismguard.domains.registry import get_domain_pack

        pack = get_domain_pack(key)
        if pack.overlay_path.is_file():
            seed_yaml.append(pack.overlay_path)
    except ValueError:
        pass

    root = Path("benchmark") / key / "data"
    if key == "law":
        seed_yaml.extend(
            [
                root / "legal_attacks.yaml",
                root / "synthetic_attacks.yaml",
            ]
        )
        feedback_jsonl.extend(
            [
                root / "law_training_augment.jsonl",
                root / "law_benign_hard_negatives.jsonl",
            ]
        )
    elif key == "general":
        hub_root = Path("benchmark/hub/training")
        seed_yaml.append(hub_root / "hub_attacks.yaml")
        feedback_jsonl.append(hub_root / "hub_benign_hard_negatives.jsonl")
    else:
        # healthcare / finance: overlay already added; optional benchmark data if present
        for name in ("training_augment.jsonl", "benign_hard_negatives.jsonl"):
            feedback_jsonl.append(root / name)
        for name in ("attacks.yaml", "synthetic_attacks.yaml"):
            seed_yaml.append(root / name)

    return (
        [p for p in seed_yaml if p.is_file()],
        [p for p in feedback_jsonl if p.is_file()],
    )


def plan_training_corpus(
    *,
    profile: str = "full",
    feedback_paths: list[Path] | None = None,
    seed_yaml_paths: list[Path] | None = None,
    domain_pack: str | None = None,
    from_storage: bool = False,
    holdout_domain: str = "law",
    normal_txt: Path | None = None,
    normal_yaml: Path | None = None,
) -> dict:
    """Dry-run plan for customer/hub training (no train). Defaults: no domain pack."""
    from prismguard.models.train import load_corpus_for_training

    seed_paths = list(seed_yaml_paths or [])
    fb_paths = list(feedback_paths or [])
    if domain_pack:
        d_seed, d_fb = default_domain_training_paths(domain_pack)
        seed_paths.extend(d_seed)
        fb_paths.extend(d_fb)

    examples, manifest = load_corpus_for_training(
        profile=profile,  # type: ignore[arg-type]
        feedback_paths=fb_paths,
        seed_yaml_paths=seed_paths,
        from_storage=from_storage,
    )
    normal_suite = "law_normal_scenarios"
    if normal_txt is not None:
        normal_suite = str(normal_txt)
    elif normal_yaml is not None:
        normal_suite = str(normal_yaml)
    elif holdout_domain != "law":
        normal_suite = f"domain:{holdout_domain}:holdout_benign"

    return {
        "profile": profile,
        "domain_pack": domain_pack or None,
        "holdout_domain": holdout_domain,
        "normal_suite": normal_suite,
        "seed_yaml": [str(p) for p in seed_paths],
        "feedback_jsonl": [str(p) for p in fb_paths],
        "from_storage": from_storage,
        "total_examples": manifest.total_examples,
        "injection_examples": sum(1 for e in examples if e.label == 1),
        "benign_examples": sum(1 for e in examples if e.label == 0),
        "fingerprint": manifest.fingerprint,
        "sources": dict(manifest.sources),
    }


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
