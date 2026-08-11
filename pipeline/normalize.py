"""Accent- and case-folding, Latin macron stripping, key building."""

import re
import unicodedata

# Latin characters with macrons or breves -> plain ASCII fallback.
# Full mapping for the Latin etyma we encounter.
_MACRON_BREVE_MAP = str.maketrans({
    "\u0101": "a", "\u0100": "a",  # ā Ā
    "\u0113": "e", "\u0112": "e",  # ē Ē
    "\u012b": "i", "\u012a": "i",  # ī Ī
    "\u014d": "o", "\u014c": "o",  # ō Ō
    "\u016b": "u", "\u016a": "u",  # ū Ū
    "\u0115": "e", "\u0114": "e",  # ĕ Ĕ
    "\u0103": "a", "\u0102": "a",  # ă Ă
    "\u010f": "i", "\u010e": "i",  # ĭ Ĭ
    "\u014f": "o", "\u014e": "o",  # ŏ Ŏ
    "\u016d": "u", "\u016c": "u",  # ŭ Ŭ
    "\u1e13": "e", "\u1e12": "e",  # ḕ Ḕ
    "\u1e17": "e", "\u1e16": "e",  # ḗ Ḗ
    "\u1e15": "o", "\u1e14": "o",  # ḕ Ḕ
    "\u1e19": "o", "\u1e18": "o",  # ḙ Ḙ
})


def fold(text: str) -> str:
    """Casefold + strip combining diacritics -> plain ASCII lowercase.
    
    Used for accent-insensitive matching (e.g. hacer == hacér).
    NFC-normalized first so composed accented chars decompose properly.
    """
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFC", text).casefold())
    return "".join(ch for ch in decomposed if not _is_combining(ch))


def fold_latin(text: str) -> str:
    """Like fold() but also strips Latin macrons/breves for etymon matching."""
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFC", text).casefold())
    stripped = "".join(ch for ch in decomposed if not _is_combining(ch))
    return stripped.translate(_MACRON_BREVE_MAP)


def build_key(text: str) -> str:
    """Build a stable lookup key: lowercased, accent-stripped."""
    return fold(text)


def accent_strip(text: str) -> str:
    """Remove combining diacritics, keep case. Used for allomorph extraction."""
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFC", text))
    return "".join(ch for ch in decomposed if not _is_combining(ch))


def _is_combining(ch: str) -> bool:
    return 0x0300 <= ord(ch) <= 0x036F
