"""Paradigm residual key and root allomorph extraction.

For each verb lemma with a conjugation table:
1. Compute diagnostic slot forms (10 slots).
2. Derive paradigm prefix P and residual_key tuple.
3. Group verbs by identical residual_key -> paradigm buckets.
4. Compute allomorphs for any lemma (verb stems + non-verb stems).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from pipeline.normalize import fold, accent_strip


# Maximum bucket size for family-forming: larger = regular productive class.
_MAX_FAMILY_BUCKET = 40

# Closed Spanish prefix list for allomorph matching.
_SPANISH_PREFIXES = sorted([
    "des", "re", "con", "contra", "en", "em", "entre", "mal", "bien",
    "sobre", "sub", "super", "tras", "trans", "pre", "pro", "ante",
    "anti", "in", "im", "ex", "extra", "per", "que", "satis", "semi",
    "auto", "co", "circun", "inter", "intra", "retro", "ultra", "vice",
    "pos", "post", "a",
], key=len, reverse=True)  # longest first for greedy stripping


# Spanish verbal desinence inventory (closed set, used ONLY for stripping, never building).
_DESINENCES = sorted([
    # Infinitive
    "ar", "er", "ir",
    # Gerund
    "ando", "iendo", "yendo",
    # Past participle
    "ado", "ido", "to", "so", "cho",
    # Present indicative
    "o", "as", "a", "amos", "áis", "an",
    "es", "e", "emos", "éis", "en",
    "es", "e", "imos", "ís", "en",
    # Preterite
    "é", "aste", "ó", "amos", "asteis", "aron",
    "í", "iste", "ió", "imos", "isteis", "ieron",
    # Imperfect
    "aba", "abas", "aba", "ábamos", "abais", "aban",
    "ía", "ías", "ía", "íamos", "íais", "ían",
    # Future
    "aré", "arás", "ará", "aremos", "aréis", "arán",
    "eré", "erás", "erá", "eremos", "eréis", "erán",
    "iré", "irás", "irá", "iremos", "iréis", "irán",
    # Conditional
    "aría", "arías", "aría", "aríamos", "aríais", "arían",
    "ería", "erías", "ería", "eríamos", "eríais", "erían",
    "iría", "irías", "iría", "iríamos", "iríais", "irían",
    # Present subjunctive
    "e", "es", "e", "emos", "éis", "en",
    "a", "as", "a", "amos", "áis", "an",
    # Imperfect subjunctive (-ra and -se)
    "ara", "aras", "ara", "áramos", "arais", "aran",
    "iera", "ieras", "iera", "iéramos", "ierais", "ieran",
    "ase", "ases", "ase", "ásemos", "aseis", "asen",
    "iese", "ieses", "iese", "iésemos", "ieseis", "iesen",
    # Future subjunctive
    "are", "ares", "are", "áremos", "areis", "aren",
    "iere", "ieres", "iere", "iéremos", "iereis", "ieren",
    # Imperative
    "a", "e", "ad", "ed", "id", "en", "an",
    # Bare endings (for short forms)
    "o", "a", "e", "s",
], key=len, reverse=True)  # longest first for greedy matching


def _tag_set(tags: list[str]) -> frozenset[str]:
    return frozenset(tags)


# Diagnostic slot tag patterns (each is a set of required tags).
# We match the FIRST form whose tags are a SUPERSET of the required set.
# Additional tags (like "masculine", "singular") are fine.
_SLOT_PATTERNS = [
    # 1. infinitive
    {"infinitive"},
    # 2. gerund
    {"gerund"},
    # 3. 1sg present indicative
    {"first-person", "present", "indicative", "singular"},
    # 4. 2sg present indicative (tú form, not vos)
    {"second-person", "present", "indicative", "singular"},
    # 5. 3sg present indicative
    {"third-person", "present", "indicative", "singular"},
    # 6. 1pl present indicative
    {"first-person", "present", "indicative", "plural"},
    # 7. 3sg preterite indicative
    {"third-person", "preterite", "indicative", "singular"},
    # 8. 3pl preterite indicative
    {"third-person", "preterite", "indicative", "plural"},
    # 9. 3sg present subjunctive
    {"third-person", "present", "subjunctive", "singular"},
    # 10. 3sg imperfect subjunctive (-ra, NOT -se)
    {"third-person", "imperfect", "subjunctive", "singular"},
]

_SLOT_NAMES = [
    "infinitive", "gerund", "1sg_pres_ind", "2sg_pres_ind",
    "3sg_pres_ind", "1pl_pres_ind", "3sg_pret_ind", "3pl_pret_ind",
    "3sg_pres_subj", "3sg_impf_subj",
]


def find_slot(forms: list[dict], required: set[str]) -> str | None:
    """Find the form matching the required tag set.
    
    For slot 4 (2sg present indicative), exclude vos-form.
    For slot 10 (imperfect subjunctive), exclude imperfect-se (the -se variant).
    """
    for f in forms:
        tags = set(f.get("tags", []))
        
        # Skip clitic forms
        if "combined-form" in tags:
            continue
        
        # Slot 4: exclude vos-form
        if "second-person" in required and "singular" in required and "present" in required:
            if "vos-form" in tags:
                continue
        
        # Slot 10: exclude imperfect-se
        if "imperfect" in required and "subjunctive" in required:
            if "imperfect-se" in tags:
                continue
        
        if required.issubset(tags):
            return f["form"]
    return None


def compute_paradigm_key(forms: list[dict]) -> tuple[str, tuple[str, ...]] | None:
    """Compute paradigm prefix P and residual key for a verb lemma.
    
    Returns (P, residual_key) or None if any slot is missing.
    residual_key is the tuple of 10 forms with P removed.
    """
    slots = []
    for pattern in _SLOT_PATTERNS:
        form = find_slot(forms, pattern)
        if form is None:
            return None
        slots.append(form)
    
    # Compute longest common prefix of all 10 forms
    P = _longest_common_prefix(slots)
    
    # Compute residual: each form with P removed
    residual = tuple(form[len(P):] for form in slots)
    
    return P, residual


def _longest_common_prefix(strings: list[str]) -> str:
    if not strings:
        return ""
    shortest = min(strings, key=len)
    for i in range(len(shortest)):
        ch = shortest[i]
        if any(s[i] != ch for s in strings):
            return shortest[:i]
    return shortest


def build_paradigm_buckets(verbs: list[dict]) -> dict[tuple, list[int]]:
    """Group verb lemmas by residual key.
    
    Each verb dict must have: ('id', 'forms').
    Returns {residual_key: [lemma_id, ...]}.
    """
    buckets: dict[tuple, list[int]] = defaultdict(list)
    
    for v in verbs:
        forms = v.get("forms", [])
        if len(forms) < 10:
            continue
        result = compute_paradigm_key(forms)
        if result is None:
            continue
        P, residual = result
        buckets[residual].append(v["id"])
    
    return dict(buckets)


def get_family_forming_buckets(
    buckets: dict[tuple, list[int]],
    max_size: int = _MAX_FAMILY_BUCKET,
) -> dict[tuple, list[int]]:
    """Filter buckets to only those with size <= max_size (family-forming).
    Larger buckets are regular productive classes.
    """
    return {k: v for k, v in buckets.items() if len(v) <= max_size}


def compute_allomorphs(
    word: str, pos: str, forms: list[dict],
) -> set[str]:
    """Compute allomorphs for any lemma.
    
    For verbs: stems from all non-clitic forms by stripping desinences.
    For non-verbs: accent-folded citation form + stems from plural/feminine forms.
    
    Returns set of accent-folded stems of length >= 3.
    """
    stems: set[str] = set()
    
    if pos == "verb":
        for f in forms:
            form_text = f.get("form", "")
            tags = set(f.get("tags", []))
            if "combined-form" in tags:
                continue
            if "table-tags" in tags or "inflection-template" in tags:
                continue
            if "alternative" in tags or "archaic" in tags:
                continue
            stem = _strip_desinence(form_text)
            folded = accent_strip(stem)
            if len(folded) >= 3:
                stems.add(folded)
    else:
        folded_cite = accent_strip(word)
        if len(folded_cite) >= 3:
            stems.add(folded_cite)
        base_forms = [word]
        for f in forms:
            form_text = f.get("form", "")
            tags = set(f.get("tags", []))
            if "alternative" in tags or "archaic" in tags:
                continue
            base_forms.append(form_text)
        if len(base_forms) > 1:
            prefix = _longest_common_prefix([accent_strip(bf) for bf in base_forms])
            if len(prefix) >= 3:
                stems.add(prefix)
    return stems


def _strip_desinence(form: str) -> str:
    """Strip the longest matching Spanish verbal desinence from a form.
    Returns the stem (what remains after stripping)."""
    folded = accent_strip(form).lower()
    for des in _DESINENCES:
        stem_len = len(folded) - len(des)
        if folded.endswith(des) and stem_len >= 3:
            return form[:stem_len]
    return form


def strip_one_prefix(word: str) -> str:
    """Strip at most one Spanish prefix from an accent-folded word.
    
    Returns the word with the first matching prefix removed, or the original word.
    """
    folded = accent_strip(word).lower()
    for pfx in _SPANISH_PREFIXES:
        if folded.startswith(pfx) and len(folded) > len(pfx) + 2:
            return folded[len(pfx):]
    return folded
