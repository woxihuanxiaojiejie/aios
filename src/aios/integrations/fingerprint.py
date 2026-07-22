from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_fingerprint_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    stripped = normalized.strip()
    return re.sub(r"\s+", " ", stripped)


def content_fingerprint(value: str) -> str:
    normalized = normalize_fingerprint_text(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
