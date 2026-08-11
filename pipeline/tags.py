"""Map raw tag sets -> human-readable feature strings.

Covers all 144 distinct tags observed in forms[].tags plus sense-level tags.
Ordered groups: person, tense-mood, number, extras, then clitic info.
"""

from __future__ import annotations

# Canonical order for feature groups in the output string.
# Each raw tag maps to a group; groups are emitted in this order,
# with tags within a group sorted alphabetically.
_GROUP_ORDER = [
    "impersonal",           # infinitive, gerund, participle
    "tense",                # present, preterite, imperfect, future, conditional
    "mood",                 # indicative, subjunctive, imperative
    "person",               # first-person, second-person, third-person
    "number",               # singular, plural
    "gender",               # masculine, feminine
    "formality",            # informal, formal
    "voseo",                # vos-form, with-tú, with-vos
    "aspect",               # imperfect, perfect, past
    "voice",                # (rare in Spanish, but canonical)
    "variant",              # imperfect-se, negative
    "extra",                # alternative, archaic
    "clitic",               # combined-form, accusative, dative, object-*
]

# Master dictionary: raw tag -> (group, human string).
_TAG_MAP: dict[str, tuple[str, str]] = {
    # --- impersonal forms ---
    "infinitive":  ("impersonal", "infinitive"),
    "gerund":      ("impersonal", "gerund"),
    "participle":  ("impersonal", "participle"),
    
    # --- tense ---
    "present":    ("tense", "present"),
    "preterite":  ("tense", "preterite"),
    "imperfect":  ("tense", "imperfect"),
    "future":     ("tense", "future"),
    "conditional":("tense", "conditional"),
    
    # --- mood ---
    "indicative":  ("mood", "indicative"),
    "subjunctive": ("mood", "subjunctive"),
    "imperative":  ("mood", "imperative"),
    
    # --- person ---
    "first-person":  ("person", "1st"),
    "second-person": ("person", "2nd"),
    "third-person":  ("person", "3rd"),
    "second-person-semantically": ("person", "2nd"),  # merged
    
    # --- number ---
    "singular": ("number", "singular"),
    "plural":   ("number", "plural"),
    
    # --- gender ---
    "masculine": ("gender", "masculine"),
    "feminine":  ("gender", "feminine"),
    
    # --- formality ---
    "formal":   ("formality", "formal"),
    "informal": ("formality", "informal"),
    
    # --- voseo ---
    "vos-form":    ("voseo", "vos"),
    "with-tú":     ("voseo", "tú"),
    "with-vos":    ("voseo", "vos"),
    "with-voseo":  ("voseo", "vos"),
    
    # --- aspect ---
    "past":      ("aspect", "past"),
    "perfect":   ("aspect", "perfect"),
    
    # --- variant ---
    "imperfect-se": ("variant", "-se"),
    "negative":     ("variant", "negative"),
    
    # --- extra ---
    "alternative": ("extra", "alternative"),
    "archaic":     ("extra", "archaic"),
    
    # --- clitic ---
    # The object-* tags describe the clitic itself (person, number,
    # gender); together with the case tags they are rendered as a single
    # '<person> <number> [<gender>] <case> clitic' descriptor.
    "combined-form":       ("clitic", "combined"),
    "accusative":          ("clitic", "accusative"),
    "dative":              ("clitic", "dative"),
    "object-first-person": ("clitic", "1st"),
    "object-second-person":("clitic", "2nd"),
    "object-third-person": ("clitic", "3rd"),
    "object-singular":     ("clitic", "singular"),
    "object-plural":       ("clitic", "plural"),
    "object-masculine":    ("clitic", "masculine"),
    "object-feminine":     ("clitic", "feminine"),
}

# Tags we explicitly drop during rendering (they carry no human meaning).
_DROP_TAGS = frozenset({
    "form-of", "alt-of", "table-tags", "inflection-template",
    "error-unrecognized-form",
})


def humanize(tags: list[str]) -> str:
    """Convert a list of raw tags into a single readable string.
    
    Example:
        ["first-person","indicative","present","singular"]
        -> "present indicative, 1st singular"
    
        ["feminine","plural"]
        -> "feminine plural"
    
        ["combined-form","accusative","object-third-person","object-singular","infinitive"]
        -> "infinitive + 3rd singular accusative clitic"
    """
    if not tags:
        return ""
    
    # Group recognized tags.
    groups: dict[str, list[str]] = {g: [] for g in _GROUP_ORDER}
    clitic_parts: list[str] = []
    extras: list[str] = []
    
    for tag in tags:
        if tag in _DROP_TAGS:
            continue
        mapped = _TAG_MAP.get(tag)
        if mapped:
            group, human = mapped
            groups[group].append(human)
        else:
            extras.append(tag)
    
    parts: list[str] = []
    
    # Impersonal forms (infinitive, gerund, participle) get placed first.
    imp = groups.get("impersonal", [])
    if imp:
        parts.append(" ".join(sorted(imp, key=_clitic_priority)))
    
    # Tense-mood cluster
    tense = groups.get("tense", [])
    mood = groups.get("mood", [])
    if tense or mood:
        tm = tense + mood
        parts.append(" ".join(sorted(tm, key=_clitic_priority)))
    
    # Person + number
    person = groups.get("person", [])
    number = groups.get("number", [])
    if person or number:
        pn = person + number
        parts.append(" ".join(sorted(pn, key=_clitic_priority)))
    
    # Gender
    gender = groups.get("gender", [])
    if gender:
        parts.append(" ".join(sorted(gender)))
    
    # Formality
    formal = groups.get("formality", [])
    if formal:
        parts.append(", ".join(sorted(formal)))
    
    # Voseo
    voseo = groups.get("voseo", [])
    if voseo:
        parts.append("(" + "/".join(sorted(set(voseo))) + ")")
    
    # Aspect
    aspect = groups.get("aspect", [])
    if aspect:
        parts.append(" ".join(aspect))
    
    # Variant
    variant = groups.get("variant", [])
    if variant:
        parts.append("(" + " ".join(variant) + ")")
    
    # Extra
    extra = groups.get("extra", [])
    if extra:
        parts.append(", ".join(sorted(extra)))
    
    # Clitic-bearing analyses: "<host> + <clitic descriptor>", with the
    # host rendered space-joined (e.g. "imperative 2nd singular + 1st
    # singular dative clitic"). Unmapped tags trail after " | ".
    clitic = groups.get("clitic", [])
    clitic_descriptors = _build_clitic_descriptors(clitic)
    
    if clitic_descriptors:
        host = " ".join(p for p in parts if p)
        clitic_str = " + ".join(clitic_descriptors)
        if extras:
            clitic_str += " | " + " | ".join(sorted(extras, key=str.lower))
        if host:
            return f"{host} + {clitic_str}"
        return clitic_str
    
    if extras:
        parts.append(" | ".join(sorted(extras, key=str.lower)))
    
    return ", ".join(p for p in parts if p)


def _clitic_priority(human: str) -> int:
    """Order within a group: put impersonal forms first."""
    return 0 if human in ("infinitive", "gerund", "participle") else 1


_CLITIC_PERSON = frozenset({"1st", "2nd", "3rd"})
_CLITIC_NUMBER = frozenset({"singular", "plural"})
_CLITIC_GENDER = frozenset({"masculine", "feminine"})
_CLITIC_CASE = frozenset({"accusative", "dative"})


def _build_clitic_descriptors(clitic_parts: list[str]) -> list[str]:
    """Build '<person> <number> [<gender>] <case> clitic' descriptors.

    The clitic group holds one entry per object-*/case tag plus the
    'combined' marker. One descriptor is produced per clitic; when two
    clitics are present their parts are aligned by position. A clitic
    without an explicit case still gets a descriptor ('1st singular
    clitic').
    """
    persons = [p for p in clitic_parts if p in _CLITIC_PERSON]
    numbers = [n for n in clitic_parts if n in _CLITIC_NUMBER]
    genders = [g for g in clitic_parts if g in _CLITIC_GENDER]
    cases = [c for c in clitic_parts if c in _CLITIC_CASE]
    n = max(len(persons), len(numbers), len(genders), len(cases))
    descriptors = []
    for i in range(n):
        person = persons[i] if i < len(persons) else (persons[-1] if persons else "")
        number = numbers[i] if i < len(numbers) else (numbers[-1] if numbers else "")
        gender = genders[i] if i < len(genders) else (genders[-1] if genders else "")
        case = cases[i] if i < len(cases) else (cases[-1] if cases else "")
        bits = [b for b in (person, number, gender, case) if b]
        descriptors.append(" ".join(bits) + " clitic" if bits else "clitic")
    return descriptors


# ---------------------------------------------------------------------------
# Canonical ordering of form analyses (form.features)
# ---------------------------------------------------------------------------

_NON_FINITE_WORDS = ("infinitive", "gerund", "participle")
_TENSE_RANK = {
    "present": 0, "imperfect": 1, "preterite": 2,
    "future": 3, "conditional": 4,
}
_PERSON_INDEX = {"1st": 0, "2nd": 1, "3rd": 2}


def _feature_mood_rank(feature: str) -> int:
    """Mood bucket: non-finite < indicative < subjunctive < imperative < clitic < other.

    A clitic-bearing analysis ('gerund + 3rd singular accusative clitic')
    is bucketed as clitic-bearing, not by its host's mood, so the clitic
    check comes first. Trailing unmapped tags (' | ...') are ignored.
    """
    if feature.split(" | ")[0].rstrip().endswith("clitic"):
        return 4
    if any(m in feature for m in _NON_FINITE_WORDS):
        return 0
    if "indicative" in feature:
        return 1
    if "subjunctive" in feature:
        return 2
    if "imperative" in feature:
        return 3
    return 5


def _feature_tense_rank(feature: str) -> int:
    """Tense within a mood: present < imperfect < preterite < future < conditional."""
    for tense, rank in _TENSE_RANK.items():
        if tense in feature:
            return rank
    return -1


def _feature_person_rank(feature: str) -> int:
    """Person rank: 1sg < 2sg < 3sg < 1pl < 2pl < 3pl (no person sorts first)."""
    for p, idx in _PERSON_INDEX.items():
        if p in feature:
            return idx + (3 if "plural" in feature else 0)
    return -1


def feature_sort_key(feature: str) -> tuple:
    """Canonical sort key for form analyses.

    Mood order: non-finite (infinitive, gerund, participle) -> indicative
    -> subjunctive -> imperative -> clitic-bearing -> anything else; within
    a mood by tense (present, imperfect, preterite, future, conditional),
    then by person (1sg, 2sg, 3sg, 1pl, 2pl, 3pl).
    """
    return (
        _feature_mood_rank(feature),
        _feature_tense_rank(feature),
        _feature_person_rank(feature),
        feature,
    )
