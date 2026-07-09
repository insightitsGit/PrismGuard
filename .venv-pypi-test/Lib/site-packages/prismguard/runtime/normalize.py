from __future__ import annotations

import base64
import re
import unicodedata

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
_B64_LIKE = re.compile(r"(?:[A-Za-z0-9+/]{20,}={0,2})")
_HEX_EMBEDDED = re.compile(r"0x[0-9a-fA-F]{6,}")


def normalize_prompt(text: str, *, max_obfuscation_depth: int = 3) -> str:
    """Unicode NFKC, zero-width strip, recursive light obfuscation decode."""
    current = unicodedata.normalize("NFKC", text)
    current = _ZERO_WIDTH.sub("", current)
    current = current.strip()

    for _ in range(max_obfuscation_depth):
        decoded = _try_decode_layer(current)
        if decoded is None or decoded == current:
            break
        current = decoded
    return current.lower()


def _try_decode_layer(text: str) -> str | None:
    b64_match = _B64_LIKE.search(text)
    if b64_match:
        token = b64_match.group(0)
        try:
            raw = base64.b64decode(token, validate=True)
            decoded = raw.decode("utf-8")
            if decoded and decoded != token:
                return text.replace(token, decoded, 1)
        except (ValueError, UnicodeDecodeError):
            pass

    hex_match = _HEX_EMBEDDED.search(text)
    if hex_match:
        token = hex_match.group(0)
        try:
            decoded = bytes.fromhex(token[2:]).decode("utf-8")
            if decoded and decoded != token:
                return text.replace(token, decoded, 1)
        except (ValueError, UnicodeDecodeError):
            pass
    return None
