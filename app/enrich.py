"""Phase 1 dashboard enrichment: the new ``/api/analyze`` keys.

Pure functions shared by both backends (``app/store_sqlite.py`` and
``app/store_fixture.py``) so the contract shapes cannot drift. No DB access
here — callers pass the pieces they already fetched.

Produces, per the frozen §D contract of docs/DESIGN_IMPLEMENTATION_PLAN.md:

- ``morphology`` — two-way lexeme/morpheme split, base, categoría,
  conjugación, decomposition accordion, ranked ambiguity alternatives.
- ``summary`` — the Spanish grammatical line.
- ``familyPreview`` — hub + satellites ranked (relation type, frequency,
  POS diversity), searched form flagged.
- ``origin`` — the etymological chain, ``sourceMeaning`` always null in
  Phase 1 (no Latin-gloss source exists; see docs F7).
- ``nearbyForms`` — the same-tense paradigm row for verb forms.

The lexeme split reuses the closed desinence inventory from
``pipeline/paradigm.py`` (single source of truth — nothing is duplicated)
but does NOT reuse ``paradigm._strip_desinence`` as-is: that function folds
the surface form but not the inventory entries, so accented desinences
never match (``hablábamos`` → ``habláb + -amos``) and the greedy longest
match over-strips participle endings onto finite forms (``canto`` → ``can-
+ -to``). Displaying either would be a wrong split. Instead the same closed
inventory is matched accent-insensitively and the chosen desinence must be
consistent with the form's own grammatical analysis (cell groups mirror the
comment grouping in ``pipeline/paradigm.py`` verbatim; an import-time
assertion keeps the two in lockstep). A split that cannot be made correctly
is never emitted: ``lexeme``/``inflection`` are null and the docs' empty
states apply.
"""

from __future__ import annotations

from pipeline.normalize import fold
from pipeline.paradigm import _DESINENCES

# ---------------------------------------------------------------------------
# Closed Spanish vocabulary: POS labels, language labels, feature words.
# ---------------------------------------------------------------------------

_POS_LABELS_ES = {
    "verb": "verbo", "noun": "sustantivo", "adj": "adjetivo", "adv": "adverbio",
    "name": "nombre propio", "pron": "pronombre", "det": "determinante",
    "article": "artículo", "num": "numeral", "prep": "preposición",
    "conj": "conjunción", "intj": "interjección", "particle": "partícula",
    "suffix": "sufijo", "prefix": "prefijo", "interfix": "interfijo",
    "infix": "infijo", "phrase": "locución", "proverb": "refrán",
    "contraction": "contracción", "symbol": "símbolo", "punct": "puntuación",
    "character": "carácter", "prep_phrase": "locución preposicional",
    "adv_phrase": "locución adverbial",
}


def spanish_pos_label(pos: str) -> str:
    return _POS_LABELS_ES.get(pos, pos)


# Language code -> Spanish label. Covers the codes in pipeline/build.py's
# ``_LANG_LABELS``; unmapped codes fall back to the stored English label
# (rare, and better than blank). Proto-language names come from the same map.
_LANG_LABELS_ES = {
    "la": "latín", "la-lat": "latín tardío", "la-vul": "latín vulgar",
    "la-med": "latín medieval", "la-eme": "latín medieval temprano",
    "la-ecc": "latín eclesiástico", "la-new": "latín moderno",
    "osp": "español antiguo", "es": "español", "fro": "francés antiguo",
    "frm": "francés medio", "fr": "francés", "it": "italiano",
    "pt": "portugués", "ca": "catalán", "oc": "occitano", "ro": "rumano",
    "ine-pro": "protoindoeuropeo", "itc-pro": "protoitálico",
    "gem-pro": "protogermánico", "cel-pro": "protocéltico",
    "grk-pro": "protogriego", "sla-pro": "protoeslavo",
    "bat-pro": "protobáltico", "sem-pro": "protosemítico",
    "afa-pro": "protoafroasiático", "ine": "indoeuropeo",
    "qfa-sub": "sustrato", "ar": "árabe", "xaa": "árabe andalusí",
    "got": "gótico", "grc": "griego antiguo", "nah": "náhuatl",
    "nci": "náhuatl clásico", "qu": "quechua", "eu": "vasco",
    "en": "inglés", "de": "alemán", "nl": "neerlandés", "sa": "sánscrito",
    "ja": "japonés", "he": "hebreo", "frk": "franco", "pro": "occitano antiguo",
    "tnq": "taíno", "arn": "mapudungun", "ota": "turco otomano",
    "mis": "sin clasificar",
}


def spanish_lang_label(lang: str, fallback: str = "") -> str:
    if lang in _LANG_LABELS_ES:
        return _LANG_LABELS_ES[lang]
    return fallback


# ---------------------------------------------------------------------------
# Feature parsing: the humanized analysis strings are a closed vocabulary
# (``pipeline/tags.py`` ``humanize`` + the fixture's older spelling). Both
# spellings ("1st" vs "first-person") must parse.
# ---------------------------------------------------------------------------

# token -> (kind, value). Kinds: person, number, gender, tense, mood,
# nonfinite, aspect, degree, extra, clitic, ignore.
_FEATURE_WORDS: dict[str, tuple[str, object]] = {
    # person (SQLite spelling "1st"; fixture spelling "first-person")
    "1st": ("person", 1), "2nd": ("person", 2), "3rd": ("person", 3),
    "first-person": ("person", 1), "second-person": ("person", 2),
    "third-person": ("person", 3),
    # number / gender
    "singular": ("number", "singular"), "plural": ("number", "plural"),
    "masculine": ("gender", "masculine"), "feminine": ("gender", "feminine"),
    # tense
    "present": ("tense", "present"), "preterite": ("tense", "preterite"),
    "imperfect": ("tense", "imperfect"), "future": ("tense", "future"),
    "conditional": ("tense", "conditional"), "pluperfect": ("tense", "pluperfect"),
    # mood
    "indicative": ("mood", "indicative"), "subjunctive": ("mood", "subjunctive"),
    "imperative": ("mood", "imperative"),
    # non-finite
    "infinitive": ("nonfinite", "infinitive"), "gerund": ("nonfinite", "gerund"),
    "participle": ("nonfinite", "participle"),
    # aspect / degree / extras
    "perfect": ("aspect", "perfect"), "past": ("aspect", "past"),
    "progressive": ("aspect", "progressive"),
    "diminutive": ("degree", "diminutive"), "augmentative": ("degree", "augmentative"),
    "superlative": ("degree", "superlative"), "comparative": ("degree", "comparative"),
    "informal": ("extra", "informal"), "formal": ("extra", "formal"),
    "voseo": ("extra", "voseo"), "alternative": ("extra", "alternative"),
    "archaic": ("extra", "archaic"), "negative": ("extra", "negative"),
    "reflexive": ("extra", "reflexive"), "-ra": ("extra", "-ra"),
    "-se": ("extra", "-se"),
    # clitic markers
    "clitic": ("clitic", True), "stack": ("clitic", True),
    "object": ("clitic", True), "accusative": ("clitic", True),
    "dative": ("clitic", True), "combined": ("clitic", True),
    "direct": ("clitic", True), "direct-object": ("clitic", True),
    # ignorable (known, carry no grammar)
    "person": ("ignore", None), "citation": ("ignore", None),
    "form": ("ignore", None), "fixed": ("ignore", None),
    "phrase": ("ignore", None), "compound": ("ignore", None),
    "acabar": ("ignore", None), "de": ("ignore", None), "estar": ("ignore", None),
    "a": ("ignore", None), "punto": ("ignore", None), "soler": ("ignore", None),
    "tener": ("ignore", None), "que": ("ignore", None), "ir": ("ignore", None),
    "+": ("ignore", None),
}


class FeatureParts:
    """Parsed grammatical content of one analysis string."""

    __slots__ = ("tense", "mood", "nonfinite", "person", "number", "gender",
                 "aspect", "degree", "extras", "clitic", "unclean")

    def __init__(self):
        self.tense: str | None = None
        self.mood: str | None = None
        self.nonfinite: str | None = None
        self.person: int | None = None
        self.number: str | None = None
        self.gender: str | None = None
        self.aspect: str | None = None
        self.degree: str | None = None
        self.extras: list[str] = []
        self.clitic = False
        self.unclean = False  # unknown words or contradictory properties


def _tokenize(feature: str) -> list[str]:
    tokens: list[str] = []
    for piece in feature.split(","):
        for tok in piece.split():
            tok = tok.strip("()")
            if tok:
                tokens.append(tok)
    return tokens


_CLITIC_WORDS = frozenset(
    w for w, (kind, _) in _FEATURE_WORDS.items() if kind == "clitic"
)


def parse_feature(feature: str) -> FeatureParts:
    """Parse one humanized analysis string.

    ``unclean`` marks analyses with unknown words (junk like "o-ue
    alternation") or contradictory properties (kaikki's preterite artifact
    "present preterite indicative" carries two tenses). Clean analyses only
    ever come from the closed vocabulary.

    After the first clitic marker or ``+`` (kaikki's clitic-descriptor
    syntax "infinitive + 3rd singular accusative clitic"), person/number/
    gender words describe the CLITIC, not the main analysis, and are
    ignored — the clitic's person must not conflict with the main verb's.
    """
    parts = FeatureParts()
    in_clitic = False
    for tok in _tokenize(feature):
        if tok == "+" or tok in _CLITIC_WORDS:
            in_clitic = True
            parts.clitic = True
            continue
        if in_clitic and tok in ("person", "1st", "2nd", "3rd",
                                 "first-person", "second-person", "third-person",
                                 "singular", "plural", "masculine", "feminine"):
            continue  # the clitic's own person/number/gender
        kind, value = _FEATURE_WORDS.get(tok, (None, None))
        if kind is None:
            parts.unclean = True
            continue
        if kind == "person":
            if parts.person is not None and parts.person != value:
                parts.unclean = True
            parts.person = value
        elif kind == "tense":
            if parts.tense is not None and parts.tense != value:
                parts.unclean = True  # e.g. "present preterite indicative"
            parts.tense = value
        elif kind == "mood":
            if parts.mood is not None and parts.mood != value:
                parts.unclean = True
            parts.mood = value
        elif kind == "number":
            parts.number = value
        elif kind == "gender":
            parts.gender = value
        elif kind == "nonfinite":
            parts.nonfinite = value
        elif kind == "aspect":
            parts.aspect = value
        elif kind == "degree":
            parts.degree = value
        elif kind == "extra":
            if value not in parts.extras:
                parts.extras.append(value)
        elif kind == "clitic":
            parts.clitic = True
    return parts


def _has_any_meaning(parts: FeatureParts) -> bool:
    return any((parts.tense, parts.mood, parts.nonfinite, parts.person,
                parts.number, parts.gender, parts.aspect, parts.degree))


def pick_clean_analysis(features: list[str]) -> FeatureParts | None:
    """The first/cleanest analysis (docs F12): never concatenate analyses.

    Deterministic: the first clean analysis that is not a clitic analysis
    wins (the source lists the plain interpretation first for clitic forms
    such as ``hacerse``); failing that, the first clean analysis; else the
    first analysis that carries any parseable grammar; else None.
    """
    if not features:
        return None
    first_meaningful: FeatureParts | None = None
    first_plain: FeatureParts | None = None
    for feature in features:
        parts = parse_feature(feature)
        if parts.unclean or not _has_any_meaning(parts):
            continue
        if first_meaningful is None:
            first_meaningful = parts
        if not parts.clitic and first_plain is None:
            first_plain = parts
    return first_plain if first_plain is not None else first_meaningful


# Spanish rendering ---------------------------------------------------------

_TENSE_ES = {
    "present": "presente", "preterite": "pretérito perfecto simple",
    "imperfect": "pretérito imperfecto", "future": "futuro",
    "conditional": "condicional", "pluperfect": "pretérito pluscuamperfecto",
}

_NONFINITE_ES = {"infinitive": "infinitivo", "gerund": "gerundio", "participle": "participio"}

_MOOD_ES = {"indicative": "indicativo", "subjunctive": "subjuntivo", "imperative": "imperativo"}

_DEGREE_ES = {"diminutive": "diminutivo", "augmentative": "aumentativo",
              "superlative": "superlativo", "comparative": "comparativo"}

_PERSON_ES = {1: "1ª", 2: "2ª", 3: "3ª"}


def _tense_phrase(parts: FeatureParts) -> str | None:
    """Tense + aspect -> Spanish, e.g. ``presente perfecto``, ``condicional``."""
    words = []
    if parts.tense == "pluperfect":
        words.append("pretérito pluscuamperfecto")
    elif parts.tense:
        words.append(_TENSE_ES.get(parts.tense, parts.tense))
        if parts.aspect == "perfect":
            words.append("perfecto")
    if parts.aspect == "progressive":
        words.append("progresivo")
    return " ".join(words) if words else None


def spanish_summary(pos: str, features: list[str]) -> str:
    """The plain-language grammatical line (design.md §13 / mockup):
    ``verbo · modo indicativo · pretérito imperfecto · 1ª persona del plural``.
    Falls back to the POS label alone when nothing parses."""
    label = spanish_pos_label(pos)
    parts = pick_clean_analysis(features)
    if parts is None:
        return label

    out = [label]
    if "reflexive" in parts.extras:
        out[0] = f"{label} reflexivo"

    if parts.nonfinite:
        out.append("no personal")
        out.append(_NONFINITE_ES.get(parts.nonfinite, parts.nonfinite))
        if parts.nonfinite == "participle" and parts.aspect == "past":
            out[-1] = "participio pasado"
    else:
        mood = parts.mood or ("indicative" if parts.tense else None)
        if mood:
            out.append(f"modo {_MOOD_ES.get(mood, mood)}")
        phrase = _tense_phrase(parts)
        if phrase:
            out.append(phrase)

    if parts.person is not None and parts.number:
        out.append(f"{_PERSON_ES.get(parts.person, '')} persona del {parts.number}")
    elif pos in ("noun", "adj"):
        bits = []
        if parts.gender:
            bits.append("masculino" if parts.gender == "masculine" else "femenino")
        if parts.number:
            bits.append("singular" if parts.number == "singular" else "plural")
        if bits:
            out.append(" ".join(bits))
    if parts.degree:
        out.append(_DEGREE_ES.get(parts.degree, parts.degree))
    if parts.clitic:
        out.append("con clítico")
    return " · ".join(out)


def desinence_label(features: list[str]) -> str:
    """Spanish label for the inflection row / decomposition accordion."""
    parts = pick_clean_analysis(features)
    if parts is None:
        return "desinencia flexiva"
    phrase = _tense_phrase(parts)
    if parts.person is not None and parts.number:
        person = f"{_PERSON_ES.get(parts.person, '')} persona del {parts.number}"
        if phrase:
            return f"desinencia de {phrase}, {person}"
        return f"desinencia de {person}"
    if phrase:
        return f"desinencia de {phrase}"
    return "desinencia flexiva"


# ---------------------------------------------------------------------------
# Lexeme / inflection split (the closed-inventory, feature-guided split).
# ---------------------------------------------------------------------------

# Closed enclitic set, sorted longest-first for greedy stripping. Proclitic
# forms ("me doy") are multi-word surfaces and are rejected by the junk
# guard before we ever get here.
_CLITICS = sorted(("me", "te", "se", "nos", "os", "le", "les", "lo", "la",
                   "los", "las"), key=len, reverse=True)

# Desinence cell groups, transcribed verbatim from the comment grouping in
# pipeline/paradigm.py (same entries, same groups — the import-time assert
# below pins them to the single source of truth). Used ONLY to select which
# inventory desinence may realize a given analysis: a form analysed as
# present indicative must not split with a participle desinence.
_FINITE_CELLS: dict[tuple[str | None, str | None], tuple[str, ...]] = {
    ("indicative", "present"): ("o", "as", "a", "amos", "áis", "an",
                                "es", "e", "emos", "éis", "en",
                                "es", "e", "imos", "ís", "en"),
    ("indicative", "preterite"): ("é", "aste", "ó", "amos", "asteis", "aron",
                                  "í", "iste", "ió", "imos", "isteis", "ieron"),
    ("indicative", "imperfect"): ("aba", "abas", "aba", "ábamos", "abais", "aban",
                                  "ía", "ías", "ía", "íamos", "íais", "ían"),
    ("indicative", "future"): ("aré", "arás", "ará", "aremos", "aréis", "arán",
                               "eré", "erás", "erá", "eremos", "eréis", "erán",
                               "iré", "irás", "irá", "iremos", "iréis", "irán"),
    ("indicative", "conditional"): ("aría", "arías", "aría", "aríamos", "aríais", "arían",
                                    "ería", "erías", "ería", "eríamos", "eríais", "erían",
                                    "iría", "irías", "iría", "iríamos", "iríais", "irían"),
    ("subjunctive", "present"): ("e", "es", "e", "emos", "éis", "en",
                                 "a", "as", "a", "amos", "áis", "an"),
    ("subjunctive", "imperfect"): ("ara", "aras", "ara", "áramos", "arais", "aran",
                                   "iera", "ieras", "iera", "iéramos", "ierais", "ieran",
                                   "ase", "ases", "ase", "ásemos", "aseis", "asen",
                                   "iese", "ieses", "iese", "iésemos", "ieseis", "iesen"),
    ("subjunctive", "future"): ("are", "ares", "are", "áremos", "areis", "aren",
                                "iere", "ieres", "iere", "iéremos", "iereis", "ieren"),
    ("imperative", None): ("a", "e", "ad", "ed", "id", "en", "an"),
}

_NONFINITE_CELLS: dict[str, tuple[str, ...]] = {
    "infinitive": ("ar", "er", "ir"),
    "gerund": ("ando", "iendo", "yendo"),
    "participle": ("ado", "ido", "to", "so", "cho"),
}

# The "bare endings" group from paradigm.py — valid for short/finite forms
# whose exact cell is uncertain ("present, 1st singular" carries no mood).
_BARE_ENDINGS = ("o", "a", "e", "s")

_assert_all_cells_members_of_inventory = all(
    des in _DESINENCES
    for cell in (*_FINITE_CELLS.values(), *_NONFINITE_CELLS.values(), _BARE_ENDINGS)
    for des in cell
)
assert _assert_all_cells_members_of_inventory, (
    "enrich.py desinence cells drifted from pipeline/paradigm.py _DESINENCES — "
    "update the cell tables from the inventory's comment grouping"
)


def _candidate_desinences(parts: FeatureParts) -> tuple[str, ...]:
    """Inventory desinences consistent with the form's analysis."""
    if parts.nonfinite:
        return _NONFINITE_CELLS[parts.nonfinite]
    cells = []
    for (mood, tense), desinences in _FINITE_CELLS.items():
        if parts.mood and mood != parts.mood:
            continue
        if parts.tense and tense != parts.tense:
            continue
        if mood == "imperative" and parts.mood != "imperative":
            continue  # the imperative cell only realizes imperative analyses
        cells.append(desinences)
    if not cells:
        cells.append(_BARE_ENDINGS)
    out: list[str] = []
    for cell in cells:
        for des in cell:
            if des not in out:
                out.append(des)
    return tuple(out)


def _strip_desinence_for(form: str, parts: FeatureParts) -> tuple[str, str] | None:
    """Longest inventory desinence consistent with the analysis, accent-
    insensitive on BOTH sides. Returns (stem, desinence) from the original
    surface form, or None when no consistent desinence fits."""
    folded = fold(form)
    candidates = _candidate_desinences(parts)
    for des in sorted(candidates, key=len, reverse=True):
        stem_len = len(folded) - len(fold(des))
        if folded.endswith(fold(des)) and stem_len >= 3:
            return form[:stem_len], form[stem_len:]
    return None


def _strip_clitics_verified(folded: str, known_folded: set[str]) -> str | None:
    """Strip trailing enclitics, verifying every intermediate against the
    lemma's own form table. None when the chain cannot be fully verified —
    never a guess. The remainder guard is >= 2 chars so two-letter bases
    participate ("vete" → "ve" is a known form of ir), and every stripped
    candidate must itself be a known form, so nothing is ever guessed."""
    remainder = folded
    stripped_any = False
    while True:
        hit = None
        for cl in _CLITICS:
            if remainder.endswith(cl) and len(remainder) - len(cl) >= 2:
                candidate = remainder[: -len(cl)]
                if candidate in known_folded:
                    hit = cl
                    break
        if hit is None:
            return remainder if stripped_any else None
        stripped_any = True
        remainder = remainder[: -len(hit)]


def _single_word_alpha(form: str) -> bool:
    """F12 junk guard: decomposition and the forms strip never run on the
    multi-word and non-alphabetic annotation rows ('o-ue alternation',
    'hacer popó', 'haber hecho', …)."""
    return bool(form) and form.isalpha()


def _any_clitic_analysis(features: list[str]) -> bool:
    return any(parse_feature(f).clitic for f in features)


def _stem_corroborated(stem: str, known_forms: list[tuple[str, list[str]]]) -> bool:
    """The naive stem of a clitic-collision surface is only trusted when at
    least one OTHER form of the same lemma splits to the same stem. This
    separates "hablo" (stem "habl", corroborated by hablas/habla/…) from
    "dese" under dar (naive stem "des" — no dar form splits to "des"; the
    surface is really "dé + se")."""
    if not stem or len(stem) < 3:
        return False
    for other, other_features in known_forms:
        if other == stem:  # the surface itself is the trivial corroboration
            continue
        if len(other) <= len(stem):
            continue
        if not _single_word_alpha(other):
            continue
        other_parts = pick_clean_analysis(other_features)
        if other_parts is None:
            continue
        result = _strip_desinence_for(other, other_parts)
        if result is not None and fold(result[0]) == fold(stem):
            return True
    return False


def split_lexeme(form: str, parts: FeatureParts | None,
                 known_forms: list[tuple[str, list[str]]],
                 features: list[str] | None = None) -> tuple[str | None, str | None]:
    """Two-way lexeme/inflection split (docs B1, rulings F9/F12).

    Returns ``(stem, desinence)`` or ``(None, None)``. A wrong split is
    never emitted: junk surfaces, unparseable analyses, unverifiable clitic
    chains, and short irregular stems all yield None and the empty state.

    The searched form is the anchor, not the lemma: ``hablábamos`` splits
    ``habl- + -ábamos``; a clitic form splits on its verified base
    (``mentirlo`` → ``ment- + -ir``) because the inflection belongs to the
    base, not the enclitic.

    Surfaces that merely LOOK clitic ("hablo" ends in -lo) fall through to
    the plain split — with the same-lemma stem corroboration as a final
    guard, so a real clitic whose base is not in the paradigm ("dese" =
    "dé + se" under dar) is nulled instead of mis-segmented.
    """
    if not _single_word_alpha(form) or parts is None:
        return None, None
    folded = fold(form)
    features = features or []

    trailing = next((cl for cl in _CLITICS if folded.endswith(cl)), None)
    if trailing is not None:
        known_folded = {fold(f) for f, _ in known_forms}
        base = _strip_clitics_verified(folded, known_folded)
        if base is not None:
            result = _strip_desinence_for(base, parts)
            return result if result is not None else (None, None)
        # Unverifiable chain: a genuinely clitic surface (any analysis
        # carries a clitic marker) can never be segmented safely.
        if _any_clitic_analysis(features):
            return None, None
        result = _strip_desinence_for(form, parts)
        if result is not None and _stem_corroborated(result[0], known_forms):
            return result
        return None, None

    return _strip_desinence_for(form, parts) or (None, None)


def decomposition_items(form: str, stem: str | None, desinence: str | None,
                        features: list[str]) -> list[dict]:
    """The "Ver descomposición morfológica" accordion (2-way, docs B1)."""
    if stem is None or desinence is None:
        return []
    return [
        {"segment": stem, "label": "raíz o base léxica", "kind": "stem"},
        {"segment": f"-{desinence}", "label": desinence_label(features), "kind": "desinence"},
    ]


def conjugation_class(lemma_word: str, pos: str) -> str | None:
    """``Primera (-ar)`` etc. — from the infinitive ending, verbs only."""
    if pos != "verb":
        return None
    if lemma_word.endswith("ar"):
        return "Primera (-ar)"
    if lemma_word.endswith("er"):
        return "Segunda (-er)"
    if lemma_word.endswith("ir"):
        return "Tercera (-ir)"
    return None


# ---------------------------------------------------------------------------
# Family preview (design.md §17-18, product spec §17-19; ruling F11).
# ---------------------------------------------------------------------------

# Relation-type priority, from the derivation tree's BFS precedence
# (pipeline/README.md): affix > paradigm > prose > root-key > derived > homograph.
_RELATION_PRIORITY = {
    "affix": 0, "paradigm": 1, "prose": 2, "root-key": 3,
    "derived": 4, "homograph": 5,
}

_PREVIEW_CAP = 10  # satellites shown around the hub


def _relation_priority(relation: str, coarse_relation: str | None = None) -> int:
    return _RELATION_PRIORITY.get(relation, _RELATION_PRIORITY.get(coarse_relation or "", 6))


def family_preview(head: dict, members: list[dict], selected_lemma_id,
                   selected_form: str, selected_pos: str, selected_gloss: str,
                   total_count: int) -> dict:
    """Hub + up to 10 satellites ranked by (relation type, frequency, POS
    diversity). The searched inflected form of the head appears as an extra
    highlighted satellite (design.md §18-19); a searched member lemma is
    flagged in place. ``members`` entries need: lemma_id, lemma, pos, gloss,
    relation, relation_label, freq, is_head, relation_priority."""
    nodes = [{
        "lemma": head["lemma"], "pos": head["pos"], "relationLabel": "root",
        "gloss": head.get("gloss") or "",
        "isSelected": bool(selected_lemma_id == head.get("lemma_id"))
        and selected_form == head["lemma"],
    }]

    satellites = [m for m in members if not m.get("is_head")]
    satellites.sort(key=lambda m: (m.get("relation_priority", 6), -m.get("freq", 0.0), m["lemma"]))

    # POS diversity: round-robin across POS groups ordered by their best
    # member's rank, so the preview mixes verbs/nouns/adjectives instead of
    # taking the first ten of one relation type.
    by_pos: dict[str, list[dict]] = {}
    for m in satellites:
        by_pos.setdefault(m["pos"], []).append(m)
    pos_order = sorted(
        by_pos,
        key=lambda p: (by_pos[p][0].get("relation_priority", 6), -by_pos[p][0].get("freq", 0.0), p),
    )
    picked: list[dict] = []
    cursor = {p: 0 for p in pos_order}
    remaining = _PREVIEW_CAP
    while remaining > 0:
        progressed = False
        for p in pos_order:
            idx = cursor[p]
            if idx < len(by_pos[p]):
                picked.append(by_pos[p][idx])
                cursor[p] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            break

    for m in picked:
        nodes.append({
            "lemma": m["lemma"], "pos": m["pos"],
            "relationLabel": m.get("relation_label") or "",
            "gloss": m.get("gloss") or "",
            "isSelected": bool(m.get("lemma_id") == selected_lemma_id),
        })

    # The searched inflected form of the head lemma is a peripheral node
    # (design.md §18: soft highlight), distinct from the hub.
    if (selected_lemma_id == head.get("lemma_id")
            and selected_form != head["lemma"]
            and _single_word_alpha(selected_form)):
        nodes.append({
            "lemma": selected_form, "pos": selected_pos, "relationLabel": "",
            "gloss": selected_gloss, "isSelected": True,
        })

    return {"hub": head["lemma"], "totalCount": total_count, "nodes": nodes}


# ---------------------------------------------------------------------------
# Origin chain (design.md §21-22, product spec §23-25; ruling F7).
# ---------------------------------------------------------------------------

_PROTO_SUFFIX = "-pro"
_PROTO_CODES = frozenset({
    "ine-pro", "itc-pro", "gem-pro", "cel-pro", "grk-pro", "sla-pro",
    "bat-pro", "sem-pro", "afa-pro", "ine", "qfa-sub",
})


def _is_proto(lang: str) -> bool:
    return lang in _PROTO_CODES or lang.endswith(_PROTO_SUFFIX)


def origin_view(ancestry: list[dict]) -> dict | None:
    """Origin card from the ancestry steps. ``ancestry`` arrives
    newest-first (the Spanish word first, etymons backwards in time) and
    ``stages`` preserves that order — the frozen §D contract documents the
    array as "oldest last, like the mockup chain", i.e. the newest stage
    (the Spanish word) is first. None when the word has no etymon data at
    all. ``sourceMeaning`` is always null in Phase 1 — no Spanish gloss of
    Latin etymons exists in any current table (docs F7)."""
    if not ancestry or len(ancestry) < 2:
        return None
    stages = list(ancestry)
    source = None
    for step in reversed(stages):  # deepest (oldest) usable non-proto step
        lang = step.get("lang") or ""
        if lang and lang != "es" and not _is_proto(lang):
            source = step
            break
    return {
        "sourceLanguage": spanish_lang_label((source or {}).get("lang") or "",
                                             (source or {}).get("lang_label") or ""),
        "sourceWord": (source or {}).get("word") or "",
        "sourceMeaning": None,
        "stages": [
            {
                "word": step.get("word") or "",
                "lang": step.get("lang") or "",
                "langLabel": spanish_lang_label(step.get("lang") or "",
                                                step.get("lang_label") or ""),
                "mode": step.get("mode"),
                "note": step.get("note"),
            }
            for step in stages
        ],
    }


# ---------------------------------------------------------------------------
# Nearby forms strip (design.md §28-29, product spec §38-39; ruling F12).
# ---------------------------------------------------------------------------

_NEARBY_CAP = 8


def _person_rank(parts: FeatureParts) -> int:
    """1sg < 2sg < 3sg < 1pl < 2pl < 3pl; no person sorts last."""
    person = parts.person or 0
    return person + (3 if parts.number == "plural" else 0) if person else 7


def nearby_forms(pos: str, searched_features: list[str],
                 forms: list[dict]) -> list[dict]:
    """Same-tense paradigm row for verb forms, capped at 8; [] for non-verbs
    and for verbs with no matching row. ``forms`` entries need: form,
    features (list of analysis strings), is_clitic, is_lemma. The searched
    form's own analysis picks the tense (e.g. ``hablábamos`` → the imperfect
    row); non-finite searches fall back to the present-indicative row."""
    if pos != "verb" or not forms:
        return []
    target = pick_clean_analysis(searched_features)
    target_tense = target.tense if target is not None else None
    if target is None or target.nonfinite or target_tense is None:
        target_mood, target_tense = "indicative", "present"
    else:
        target_mood = target.mood or "indicative"

    chosen: list[tuple[int, str, dict]] = []
    for f in forms:
        if f.get("is_clitic") or not _single_word_alpha(f.get("form") or ""):
            continue
        feats = f.get("features") or []
        best: FeatureParts | None = None
        for feat in feats:
            parts = parse_feature(feat)
            if parts.unclean or parts.nonfinite or parts.clitic:
                continue
            if parts.mood == target_mood and parts.tense == target_tense:
                if best is None or _person_rank(parts) < _person_rank(best):
                    best = parts
        if best is not None:
            chosen.append((_person_rank(best), f.get("form") or "", f))

    chosen.sort(key=lambda item: (item[0], item[1]))
    out = []
    for _, _, f in chosen[:_NEARBY_CAP]:
        out.append({
            "form": f["form"],
            "features": " \u00b7 ".join(f.get("features") or []),
            "isLemma": bool(f.get("is_lemma")),
        })
    return out
