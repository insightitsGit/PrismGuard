from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path


@dataclass(frozen=True)
class DomainPack:
    name: str
    label: str
    overlay_path: Path
    holdout_path: Path | None = None


def _pack_root() -> Path:
    return Path(resources.files("prismguard.domains"))


def list_domains() -> list[str]:
    return sorted(p.name for p in _pack_root().iterdir() if p.is_dir() and (p / "overlay.yaml").is_file())


def get_domain_pack(domain: str) -> DomainPack:
    key = domain.strip().lower()
    root = _pack_root() / key
    overlay = root / "overlay.yaml"
    if not overlay.is_file():
        known = ", ".join(list_domains()) or "(none)"
        raise ValueError(f"Unknown domain pack {domain!r}. Available: {known}")
    holdout = root / "holdout.yaml"
    labels = {
        "general": "General / web chat",
        "law": "Legal / compliance",
        "healthcare": "Healthcare / HIPAA",
        "finance": "Finance / banking",
    }
    return DomainPack(
        name=key,
        label=labels.get(key, key),
        overlay_path=overlay,
        holdout_path=holdout if holdout.is_file() else None,
    )


def domain_overlay_paths(domain: str) -> list[Path]:
    return [get_domain_pack(domain).overlay_path]
