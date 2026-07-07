from __future__ import annotations

import json
from pathlib import Path

from prismguard.seed.formats.csv_entries import parse_csv_entries
from prismguard.seed.formats.jsonl_entries import parse_jsonl_entries
from prismguard.seed.formats.markdown_seed import parse_markdown_seed
from prismguard.seed.formats.slabs_csv import parse_slabs_csv
from prismguard.seed.formats.yaml_taxonomy import parse_json_taxonomy, parse_yaml_or_json_taxonomy
from prismguard.seed.formats.yanismiraoui_csv import parse_yanismiraoui_csv
from prismguard.seed.merge import merge_parsed_seeds
from prismguard.seed.models import ParsedSeed

SUPPORTED_EXTENSIONS = {".yaml", ".yml", ".json", ".csv", ".jsonl", ".md", ".markdown"}
FormatName = str


def _detect_csv_format(path: Path) -> FormatName:
    header = path.read_text(encoding="utf-8").splitlines()[0].strip().lower()
    if header == "text,label":
        return "slabs_csv"
    if header == "prompt_injections":
        return "yanismiraoui_csv"
    if "category_slug" in header and "text" in header:
        return "csv"
    raise ValueError(f"Unknown CSV schema for {path}: {header!r}")


def detect_format(path: Path, explicit: FormatName = "auto") -> FormatName:
    if explicit != "auto":
        return explicit
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return "yaml"
    if suffix == ".json":
        return "json"
    if suffix == ".csv":
        return _detect_csv_format(path)
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in (".md", ".markdown"):
        return "markdown"
    text = path.read_text(encoding="utf-8")[:4096]
    if text.lstrip().startswith("{"):
        return "json"
    if "categories:" in text or "entries:" in text:
        return "yaml"
    if "### Categories" in text and "### Seed examples" in text:
        return "markdown"
    if "," in text.splitlines()[0] and "category_slug" in text.splitlines()[0]:
        return "csv"
    raise ValueError(f"Could not detect format for {path}")


def parse_seed_file(path: Path, *, format_name: FormatName = "auto") -> ParsedSeed:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    fmt = detect_format(resolved, format_name)
    if fmt == "yaml":
        parsed = parse_yaml_or_json_taxonomy(resolved)
    elif fmt == "json":
        parsed = parse_json_taxonomy(resolved)
    elif fmt == "csv":
        parsed = parse_csv_entries(resolved)
    elif fmt == "slabs_csv":
        parsed = parse_slabs_csv(resolved)
    elif fmt == "yanismiraoui_csv":
        parsed = parse_yanismiraoui_csv(resolved)
    elif fmt == "jsonl":
        parsed = parse_jsonl_entries(resolved)
    elif fmt == "markdown":
        parsed = parse_markdown_seed(resolved)
    else:
        raise ValueError(f"Unsupported format {fmt!r} for {resolved}")
    return parsed.with_source(str(resolved))


def _expand_source_path(path: Path, *, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(path)
    pattern = "**/*" if recursive else "*"
    files = [p for p in path.glob(pattern) if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(files)


def _read_manifest(manifest_path: Path) -> list[Path]:
    paths: list[Path] = []
    base = manifest_path.parent
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        entry = Path(value)
        if not entry.is_absolute():
            entry = base / entry
        paths.append(entry.resolve())
    return paths


def parse_seed_sources(
    sources: list[str | Path],
    *,
    format_name: FormatName = "auto",
    recursive: bool = False,
) -> ParsedSeed:
    """Parse one or many seed sources (files, directories, @manifest)."""
    file_paths: list[Path] = []
    for source in sources:
        raw = str(source)
        path = Path(raw[1:] if raw.startswith("@") else raw)
        if raw.startswith("@"):
            file_paths.extend(_read_manifest(path))
        else:
            file_paths.extend(_expand_source_path(path, recursive=recursive))

    if not file_paths:
        raise ValueError("No seed source files found")

    parsed_parts = [parse_seed_file(path, format_name=format_name) for path in file_paths]
    return merge_parsed_seeds(parsed_parts)

