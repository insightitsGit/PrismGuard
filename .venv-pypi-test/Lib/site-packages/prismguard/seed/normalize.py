from __future__ import annotations

import hashlib
import re
import unicodedata

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")


def normalize_seed_text(text: str) -> str:
    """Match runtime normalize baseline: NFKC, strip zero-width, lowercase, collapse whitespace."""
    value = unicodedata.normalize("NFKC", text)
    value = _ZERO_WIDTH.sub("", value)
    value = value.lower()
    value = re.sub(r"\s+", " ", value).strip()
    return value


def seed_content_hash(category_slug: str, text: str) -> str:
    normalized = normalize_seed_text(text)
    payload = f"{category_slug}\0{normalized}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
