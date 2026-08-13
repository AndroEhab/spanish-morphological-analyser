"""Etymology template parsing: produce typed edges for family construction.

Returns structured edges with language codes for proto-language filtering.
"""

from __future__ import annotations

import json
import re
from pipeline.normalize import fold_latin





_INTERNAL_TEMPLATES = frozenset({
    "af", "affix", "suffix", "suf", "prefix", "pre", "confix",
    "compound", "univerbation", "blend", "deverbal",
})

_INHERITED_MODES = frozenset({"inh", "inh+"})
_BORROWED_MODES = frozenset({"bor", "bor+", "lbor", "slbor", "ubor"})
_DERIVED_MODES = frozenset({"der", "uder", "dercat"})

_ETYMON_TEMPLATES = frozenset({
    "inh", "inh+", "bor", "bor+", "lbor", "slbor", "ubor",
    "der", "uder", "dercat", "etymon", "root",
})

_IGNORE_TEMPLATES = frozenset({
    "cog", "m", "m+", "ic", "yesno", "glossary", "lit", "wp", "!", ",",
})

# Language codes banned from candidate pooling: proto-languages.
_BANNED_LANG_SUFFIXES = ("-pro",)
_BANNED_LANGS = frozenset({
    "ine-pro", "itc-pro", "gem-pro", "cel-pro", "grk-pro",
    "sla-pro", "bat-pro", "ine", "qfa-sub",
})

# Map etymology-tree language names to codes.
_TREE_LANG_MAP = {
    "latin": "la", "old spanish": "osp", "spanish": "es",
    "proto-indo-european": "ine-pro", "proto-italic": "itc-pro",
    "proto-germanic": "gem-pro", "proto-celtic": "cel-pro",
    "proto-romanian": "ro", "vulgar latin": "la-vul",
    "medieval latin": "la-med", "late latin": "la-lat",
    "early medieval latin": "la-eme", "ecclesiastical latin": "la-ecc",
    "new latin": "la-new", "old french": "fro", "middle french": "frm",
    "french": "fr", "italian": "it", "portuguese": "pt",
    "catalan": "ca", "occitan": "oc", "arabic": "ar",
    "andalusian arabic": "xaa", "gothic": "got", "ancient greek": "grc",
    "nahuatl": "nah", "quechua": "qu", "english": "en",
    "german": "de", "dutch": "nl", "sanskrit": "sa",
    "proto-semitic": "sem-pro", "proto-afroasiatic": "afa-pro",
}

# Closed inventory of Spanish derivational suffixes, used to recognize a
# bare affix component by identity (wiktextract cites many affixes without
# hyphens, and template variants place them outside the positional slots).
_DERIV_SUFFIXES = frozenset({
    "miento", "cion", "sion", "dor", "dora", "ero", "era", "eria",
    "ista", "ismo", "idad", "edad", "anza", "encia", "ancia", "aje",
    "azo", "ada", "ado", "ura", "ble", "ible", "able", "oso", "osa",
    "illo", "illa", "ito", "ita", "on", "ona", "uelo", "eno", "ense",
    "ico", "al", "ar", "orio", "ivo", "ante", "ente", "mente",
})

# Closed inventory of Spanish derivational prefixes.  Mirrors
# family._SPANISH_PREFIXES (kept separate to avoid an import cycle:
# family.py imports these inventories for the form-table guard).
_DERIV_PREFIXES = frozenset({
    "des", "re", "con", "contra", "en", "em", "entre", "mal", "bien",
    "sobre", "sub", "super", "tras", "trans", "pre", "pro", "ante",
    "anti", "in", "im", "ex", "extra", "per", "satis", "semi",
    "auto", "co", "circun", "inter", "intra", "retro", "ultra", "vice",
    "pos", "post",
})


def _normalize_affix_args(name: str, parts: list[tuple[str, str]]) -> None:
    """Normalize bare affix components to hyphenated forms, in place.

    wiktextract cites affixes bare in several template shapes:
    - suffix/suf: positional rule (arg "3" = suffix) for the standard shape;
      identity fallback for the last bare component when it is a known
      derivational suffix and the positional rule did not fire.
    - prefix/pre: arg "2" = prefix (positional), else identity on the
      first bare component when it is a known prefix.
    - everything else (af/affix/confix/compound/...): identity on the
      FIRST bare component (known prefix) and the LAST bare component
      (known suffix), with two guards so a base is never reclassified:
      a bare component is not treated as a prefix when the last component
      is already hyphenated (auto + -dromo: auto is the base), and not
      treated as a suffix when the first component was hyphenated in the
      source (anti- + edad, re- + bien: the remaining bare is the base).
      With >=3 components both may fire (en- + red + -ar, geo- + centro +
      -ismo); with exactly 2 components at most one fires.

    Base slots are never reclassified by identity: the FIRST bare of
    suffix/suf and the LAST bare of prefix/pre stay bases, so a base like
    "mal" in "mal + -dad" or "oso" in "oso + -ar" survives.
    """
    def is_bare(v: str) -> bool:
        return " " not in v and not (v.startswith("-") or v.endswith("-"))
    if not parts:
        return

    if name in ("suffix", "suf"):
        if len(parts) >= 2 and parts[-1][0] == "3" and is_bare(parts[-1][1]):
            k, v = parts[-1]
            parts[-1] = (k, "-" + v)
        else:
            k, v = parts[-1]
            if is_bare(v) and v in _DERIV_SUFFIXES:
                parts[-1] = (k, "-" + v)
    elif name in ("prefix", "pre"):
        if len(parts) >= 2 and parts[0][0] == "2" and is_bare(parts[0][1]):
            k, v = parts[0]
            parts[0] = (k, v + "-")
        else:
            k, v = parts[0]
            if is_bare(v) and v in _DERIV_PREFIXES:
                parts[0] = (k, v + "-")
    else:  # af / affix / confix / compound / univerbation / blend / deverbal
        first_hyphenated = not is_bare(parts[0][1])
        last_hyphenated = not is_bare(parts[-1][1])
        prefix_taken = False
        if not last_hyphenated and is_bare(parts[0][1]) and parts[0][1] in _DERIV_PREFIXES:
            k, v = parts[0]
            parts[0] = (k, v + "-")
            prefix_taken = True
        if not first_hyphenated and is_bare(parts[-1][1]) and parts[-1][1] in _DERIV_SUFFIXES:
            if not prefix_taken or len(parts) >= 3:
                k, v = parts[-1]
                parts[-1] = (k, "-" + v)


def _detect_tree_lang(line: str) -> str | None:
    """Detect language code from an etymology tree line like 'Latin facere'."""
    stripped = line.strip().lower()
    for name, code in sorted(_TREE_LANG_MAP.items(), key=lambda x: -len(x[0])):
        if stripped.startswith(name):
            return code
    return None


def parse_templates(
    word: str,
    etym_templates_raw: str | list | None,
    etym_text: str,
) -> dict[str, list]:
    """Returns dict with keys: internal, etymons, doublets, etymtree_ancestors, prose.

    etymons: list of (ancestor_normalized, lang, mode, source_word)
    etymtree_ancestors: list of (ancestor_normalized, lang)
    prose: list of (parent_word, kind) — explicit parentage statements
        ("Deverbal from X", "Clipping of X", "From X", …) naming a Spanish
        parent.  kind is one of: deverbal, participle, clipping,
        back-formation, abbreviation, prothetic, univerbation, from,
        variant, inflection.
    """
    internal: list[tuple[str, str]] = []
    etymons: list[tuple[str, str | None, str, str]] = []  # (norm, lang, mode, src)
    doublets: list[str] = []
    etymtree_ancestors: list[tuple[str, str | None]] = []  # (norm, lang)
    prose: list[tuple[str, str]] = []  # (parent_word, kind)

    templates: list[dict] = []
    if isinstance(etym_templates_raw, str):
        try:
            templates = json.loads(etym_templates_raw)
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(etym_templates_raw, list):
        templates = etym_templates_raw

    for tmpl in templates:
        name = tmpl.get("name", "")
        args = tmpl.get("args", {})

        # INTERNAL edges
        if name in _INTERNAL_TEMPLATES and args.get("1") == "es":
            parts: list[tuple[str, str]] = []  # (key, cleaned value)
            for key in sorted(args.keys()):
                if key == "1" or not key.isdigit():
                    continue
                val = args[key]
                if val and isinstance(val, str):
                    parts.append((key, re.sub(r'<[^>]*>', '', val)))
            _normalize_affix_args(name, parts)
            _apply_alt_display(name, args, parts)
            affix_parts: list[str] = []
            bases: list[str] = []
            for k, val in parts:
                if val.startswith(":") and ":" not in val[1:]:
                    # template mode marker (:calque, :inh, :bor), not a component
                    continue
                if val.startswith("-") or val.endswith("-"):
                    affix_parts.append(val)
                elif " " not in val:
                    bases.append(val)
            if affix_parts and bases:
                # Hyphenated affixes + last base
                affix_str = " ".join(affix_parts)
                internal.append((bases[-1], affix_str))
            elif bases:
                if len(bases) >= 2:
                    # Multi-component compound: last is base, rest are affix
                    affix_str = " + ".join(bases[:-1])
                    internal.append((bases[-1], affix_str))
                else:
                    internal.append((bases[0], ""))
            # deverbal names the verb explicitly and carries no affix — the
            # parentage statement is the evidence; record it as prose.
            if name == "deverbal":
                for base, _affix in internal:
                    w = _clean_prose_word(base)
                    if w and w != word:
                        prose.append((w, "deverbal"))

        # ETY template with :af
        elif name == "ety" and args.get("1") == "es" and args.get("2") == ":af":
            parts: list[tuple[str, str]] = []
            for key in sorted(args.keys()):
                if key in ("1", "2") or not key.isdigit():
                    continue
                val = args[key]
                if val and isinstance(val, str):
                    parts.append((key, re.sub(r'<[^>]*>', '', val)))
            _normalize_affix_args("af", parts)
            _apply_alt_display("af", args, parts)
            affix_parts: list[str] = []
            bases: list[str] = []
            for k, val in parts:
                if val.startswith("-") or val.endswith("-"):
                    affix_parts.append(val)
                elif val.startswith(":") and ":" not in val[1:]:
                    # template mode marker (:calque, :inh, :bor)
                    continue
                elif ":" in val:
                    lang_part, word_part = _split_lang_word(val)
                    if lang_part in (None, "es") and " " not in word_part:
                        bases.append(word_part)
                elif " " not in val:
                    bases.append(val)
            if affix_parts and bases:
                affix_str = " ".join(affix_parts)
                internal.append((bases[-1], affix_str))
            elif bases:
                if len(bases) >= 2:
                    affix_str = " + ".join(bases[:-1])
                    internal.append((bases[-1], affix_str))
                else:
                    internal.append((bases[0], ""))

        elif name in _ETYMON_TEMPLATES or (
            name == "ety" and args.get("1") == "es"
            and str(args.get("2", "")) not in (":deverbal", ":clip", ":clipping", ":bf", ":back-formation", ":univ")
        ):
            _parse_etymon_template(name, args, etymons)

        # DOUBLET
        elif name in ("doublet", "dbt") and args.get("1") == "es":
            twin = args.get("2", "")
            if twin:
                doublets.append(twin)

        # Explicit parentage templates: ety/etymon mode markers and the
        # named clipping/back-form/abbrev/prothetic-form templates.
        elif name == "ety" and args.get("1") == "es" and str(args.get("2", "")) in (
            ":deverbal", ":clip", ":clipping", ":bf", ":back-formation", ":univ",
        ):
            kind = {
                ":deverbal": "deverbal", ":clip": "clipping", ":clipping": "clipping",
                ":bf": "back-formation", ":back-formation": "back-formation",
                ":univ": "univerbation",
            }[str(args["2"])]
            for key in ("3", "4", "5"):
                val = args.get(key, "")
                if isinstance(val, str) and val:
                    val2 = re.sub(r'<[^>]*>', '', val).strip()
                    if not val2 or " " in val2 or ":" in val2:
                        continue
                    w = _clean_prose_word(val2)
                    if w and w != word:
                        prose.append((w, kind))
        elif name == "etymon" and str(args.get("2", "")) == ":clip":
            val = args.get("3", "")
            if isinstance(val, str) and val:
                val2 = re.sub(r'<[^>]*>', '', val).strip()
                if val2 and " " not in val2:
                    w = _clean_prose_word(val2)
                    if w and w != word:
                        prose.append((w, "clipping"))
        elif name in ("clipping", "back-form", "abbrev", "prothetic form") and args.get("1") == "es":
            kind = {
                "clipping": "clipping", "back-form": "back-formation",
                "abbrev": "abbreviation", "prothetic form": "prothetic",
            }[name]
            val = args.get("2", "")
            if isinstance(val, str) and val:
                val2 = re.sub(r'<[^>]*>', '', val).strip()
                if val2 and " " not in val2:
                    w = _clean_prose_word(val2)
                    if w and w != word:
                        prose.append((w, kind))

        # surf: "By surface analysis, X + -ar" — an affix template like suffix.
        elif name == "surf" and args.get("1") == "es":
            parts: list[tuple[str, str]] = []
            for key in sorted(args.keys()):
                if key == "1" or not key.isdigit():
                    continue
                val = args[key]
                if val and isinstance(val, str):
                    parts.append((key, re.sub(r'<[^>]*>', '', val)))
            _normalize_affix_args("surf", parts)
            affix_parts: list[str] = []
            bases: list[str] = []
            for k, val in parts:
                if val.startswith("-") or val.endswith("-"):
                    affix_parts.append(val)
                elif val.startswith(":") and ":" not in val[1:]:
                    continue
                elif " " not in val:
                    bases.append(val)
            if affix_parts and bases:
                internal.append((bases[-1], " ".join(affix_parts)))
            elif len(bases) >= 2:
                internal.append((bases[-1], " + ".join(bases[:-1])))
            elif bases:
                internal.append((bases[0], ""))

    # Parse etymology_text tree with language detection
    tree_entries = _parse_etym_tree(etym_text)
    etymtree_ancestors.extend(tree_entries)
    # NOTE: tree terms are deliberately NOT linked as prose parents.
    # Etymology-tree "Spanish X" lines mix in affixes ("Spanish -eco" for
    # Chiapas + -eco) and component words that collide with unrelated
    # modern homographs; the audit's univerbation cases are already covered
    # by the :univ/:af template modes and the text patterns.
    # etymon templates naming a Spanish parent ("der|es|es|X").
    for anc, lang, mode, _src in etymons:
        if lang == "es" and mode == "derived":
            w = _clean_prose_word(anc)
            if w and w != word:
                prose.append((w, "from"))
    # Etymology prose naming a Spanish parent.
    _prose_from_text(word, etym_text, prose)

    # Deduplicate, preserving order.
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for p in prose:
        if p not in seen:
            seen.add(p)
            deduped.append(p)

    return {
        "internal": internal,
        "etymons": etymons,
        "doublets": doublets,
        "etymtree_ancestors": etymtree_ancestors,
        "prose": deduped,
    }


_PROSE_WORD = r"[^\s.,;+()\[\]<>“”‘’]+"


def _clean_prose_word(w: str) -> str:
    """Strip affix punctuation from a prose-captured parent word.

    Only plain alphabetic Spanish words are kept — tree junk like
    "probardeverb." or "parinflu." carries annotation markers that prove
    the token is not a clean parent name.
    """
    w = (w or "").strip("-–—").strip("“”'\"")
    if not w or len(w) < 2:
        return ""
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", w):
        return ""
    return w


_PROSE_MID_PATTERNS = [
    (re.compile(rf"Deverbal (?:from|of)\s+({_PROSE_WORD})", re.I), "deverbal"),
    (re.compile(rf"Past participle of\s+({_PROSE_WORD})", re.I), "participle"),
    (re.compile(rf"Clipping of\s+({_PROSE_WORD})", re.I), "clipping"),
    (re.compile(rf"Back-formation from\s+({_PROSE_WORD})", re.I), "back-formation"),
    (re.compile(rf"Abbreviation of\s+({_PROSE_WORD})", re.I), "abbreviation"),
    (re.compile(rf"inflection of (?:the verb )?({_PROSE_WORD})", re.I), "inflection"),

]


def _prose_from_text(word: str, text: str, out: list[tuple[str, str]]) -> None:
    """Conservative prose extraction for Spanish-parent statements.

    Emits the explicit parentage patterns (deverbal from X, past
    participle of X, clipping of X, back-formation from X, abbreviation
    of X, inflection of X) plus sentence-initial "From X [and/or Y]"
    candidates.  The bare "From X" candidates carry kind "from" and are
    admitted at graph-build time ONLY when the two citation forms pass
    the allomorph gate — the sentence is the evidence of connection, the
    stem overlap is the precision filter.
    """
    if not text:
        return
    t = text.strip()
    m = re.match(rf"^From\s+(?:\([^)]*\)\s+)?({_PROSE_WORD})", t)
    if m:
        raw = m.group(1)
        nxt = t[m.end():].lstrip()
        x = _clean_prose_word(raw)
        ok = (
            not nxt
            or nxt[0] in ".,;:(<>[“”‘’"
            or nxt.startswith(("and ", "by ", "or "))
        )
        # "From X- + Y" cites X as an affix — its bare form must never
        # resolve to an unrelated homograph lemma.  Only a sentence-final
        # "From super-." (a genuine clipping in prefix form) survives.
        if raw.endswith("-") and nxt not in ("", "."):
            ok = False
        if x and ok:
            if x != word:
                out.append((x, "from"))
            m2 = re.match(rf"^(?:and\s+|or\s+)({_PROSE_WORD})", nxt)
            if m2:
                y = _clean_prose_word(m2.group(1))
                if y and y != word:
                    out.append((y, "from"))
    for pat, kind in _PROSE_MID_PATTERNS:
        for m in pat.finditer(t):
            x = _clean_prose_word(m.group(1))
            if x and x != word:
                out.append((x, kind))


def _apply_alt_display(name: str, args: dict, parts: list[tuple[str, str]]) -> None:
    """Substitute altN display forms onto affix components, in place.

    wiktextract's altN keys carry the DISPLAYED form of the N-th content
    component (alt1 = first component, alt2 = second, ...).  The
    dictionary's rendered etymology uses them — pradera renders
    "prado + -era" via alt2=era on the suffix page -ero; ilegal renders
    "i- + legal" via alt1=i- — so labels must too.  Only AFFIX components
    (hyphenated parts) are substituted: bases resolve by lemma, never by
    display text.  A missing suffix/prefix slot is filled only for the
    two-part suffix/suf (alt2) and prefix/pre (alt1) templates.
    """
    for alt_key, offset in (("alt1", 0), ("alt2", 1), ("alt3", 2)):
        alt = args.get(alt_key)
        if not (isinstance(alt, str) and alt):
            continue
        alt = re.sub(r'<[^>]*>', '', alt)
        if offset < len(parts):
            k, v = parts[offset]
            if v.endswith("-"):
                parts[offset] = (k, alt if alt.endswith("-") else alt + "-")
            elif v.startswith("-"):
                parts[offset] = (k, alt if alt.startswith("-") else "-" + alt)
            # base slot: leave — bases resolve by lemma, not display text
        elif alt_key == "alt2" and name in ("suffix", "suf"):
            parts.append(("alt2", alt if alt.startswith("-") else "-" + alt))
        elif alt_key == "alt1" and name in ("prefix", "pre"):
            parts.insert(0, ("alt1", alt if alt.endswith("-") else alt + "-"))


def _parse_etymon_template(name: str, args: dict, etymons: list):
    if name in _INHERITED_MODES:
        mode = "inherited"
    elif name in _BORROWED_MODES:
        mode = "borrowed"
    elif name in _DERIVED_MODES:
        mode = "derived"
    elif name == "root":
        mode = "root"
    elif name == "ety":
        sub = args.get("2", "")
        if ":inh" in str(sub):
            mode = "inherited"
        elif ":bor" in str(sub):
            mode = "borrowed"
        elif ":der" in str(sub):
            mode = "derived"
        else:
            return
    elif name == "etymon":
        sub = args.get("2", "")
        if ":inh" in str(sub):
            mode = "inherited"
        elif ":bor" in str(sub):
            mode = "borrowed"
        elif ":der" in str(sub):
            mode = "derived"
        else:
            return
    else:
        return
    template_lang = args.get("2", None)
    # Only use template lang if it's a real language code (not ":inh", ":bor", etc.)
    if template_lang and isinstance(template_lang, str) and template_lang.startswith(":"):
        template_lang = None

    for key in ("3", "4"):
        val = args.get(key, "")
        if not val or not isinstance(val, str):
            continue
        chain = _parse_etymon_chain(val)
        for lang, w, chain_mode in chain:
            if " " in w:
                continue
            # Use template_lang as fallback when chain doesn't provide one.
            effective_lang = lang if lang else template_lang
            normalized = fold_latin(w)
            if normalized:
                etymons.append((normalized, effective_lang, chain_mode or mode, w))


def _parse_etymon_chain(raw: str) -> list[tuple[str | None, str, str | None]]:
    results: list[tuple[str | None, str, str | None]] = []
    parts = re.split(r"<(?=ety:|inh|bor|der)", raw)
    for part in parts:
        part = re.sub(r"<t:[^>]*>", "", part)
        part = re.sub(r"<pos:[^>]*>", "", part)
        part = re.sub(r"<id:[^>]*>", "", part)
        part = re.sub(r"<lit:[^>]*>", "", part)
        part = part.replace(">", "")
        if not part.strip():
            continue
        mode = None
        mode_match = re.match(r"^(?:ety:)?(inh|bor|der)<", part)
        if mode_match:
            mode = mode_match.group(1)
            part = part[mode_match.end():]
        lang, word = _split_lang_word(part)
        if word:
            # Truncate at any residual markup.  wiktextract folds display
            # forms into the etymon arg ("niger<alt:nigrum>",
            # "grātia<ref:<span…>>", "voco<") — the base form before the
            # first '<' is the etymon; the rest is annotation.
            word = word.split("<")[0].lstrip("*").strip()
            if not word:
                continue
            word = fold_latin(word)
            results.append((lang, word, mode))
    return results



def _split_lang_word(raw: str) -> tuple[str | None, str]:
    if ":" in raw:
        lang, word = raw.split(":", 1)
        return lang.strip() or None, word.strip()
    return None, raw.strip()


def _parse_etym_tree(etym_text: str) -> list[tuple[str, str | None]]:
    """Parse etymology tree lines, returning (normalized_word, lang_code, mode)."""
    if not etym_text or "Etymology tree" not in etym_text:
        return []
    results = []
    tree_start = etym_text.find("Etymology tree")
    if tree_start < 0:
        return []
    lines = etym_text[tree_start:].split("\n")
    in_tree = False
    tree_mode = None  # detect from prose after tree
    for line in lines:
        stripped = line.strip()
        if stripped == "Etymology tree":
            in_tree = True
            continue
        if not in_tree:
            continue
        if not stripped:
            break
        if re.match(r"^(Inherited|Borrowed|From|Ellipsis|Synchronically)", stripped):
            if "Inherited" in stripped:
                tree_mode = "inherited"
            elif "Borrowed" in stripped:
                tree_mode = "borrowed"
            break
        parts = stripped.rsplit(" ", 1)
        if len(parts) >= 2:
            lang_name = parts[0].strip()
            word_part = parts[-1].split("<")[0].lstrip("*").strip()
            # "Latin esseinflu." concatenates the "influenced by" marker.
            if word_part.endswith("influ."):
                word_part = word_part[:-len("influ.")].rstrip()
            if not word_part:
                continue
            lang_code = _detect_tree_lang(lang_name)
            normalized = fold_latin(word_part)
            if normalized:
                results.append((normalized, lang_code))

    return results

def is_usable_ancestor(ancestor_word: str, lang: str | None, mode: str | None = None) -> bool:
    """Check if an ancestor can be used for candidate pooling.

    Banned:
    - Proto-languages (lang ends with -pro, or in banned set)
    - Root template mode
    - Words starting with * (unattested/reconstructed)
    - Words with subscripts or annotation artifacts
    """
    if mode == "root":
        return False
    if ancestor_word.startswith("*"):
        return False
    if lang:
        if lang in _BANNED_LANGS or lang.endswith("-pro"):
            return False
    # Bogus annotation artifacts
    if re.search(r'[\u2080-\u2089\u00B2\u00B3\u00B9]', ancestor_word):
        return False
    if ancestor_word.endswith(("nom.", "bor.", "der.")):
        return False
    if ancestor_word.startswith("-") or ancestor_word.endswith("-"):
        return False
    if len(ancestor_word) < 2:
        return False
    return True
