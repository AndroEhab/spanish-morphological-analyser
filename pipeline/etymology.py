"""Etymology template parsing: produce typed edges for family construction.

Returns structured edges with language codes for proto-language filtering.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pipeline.normalize import fold_latin


_INTERNAL_TEMPLATES = frozenset({
    "af", "affix", "suffix", "suf", "prefix", "confix",
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
    """Returns dict with keys: internal, etymons, doublets, etymtree_ancestors.

    etymons: list of (ancestor_normalized, lang, mode, source_word)
    etymtree_ancestors: list of (ancestor_normalized, lang)
    """
    internal: list[tuple[str, str]] = []
    etymons: list[tuple[str, str | None, str, str]] = []  # (norm, lang, mode, src)
    doublets: list[str] = []
    etymtree_ancestors: list[tuple[str, str | None]] = []  # (norm, lang)

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
            affix_parts: list[str] = []
            bases: list[str] = []
            for key in sorted(args.keys()):
                if key == "1":
                    continue
                if key in ("text", "tree", "nocap", "nocat", "notext",
                           "t", "t1", "t2", "t3", "t4",
                           "lit", "pos", "id", "sc", "g", "g2", "g3",
                           "tr", "ts", "sort", "nl", "keyword"):
                    continue
                val = args[key]
                if val and isinstance(val, str):
                    val = re.sub(r'<[^>]*>', '', val)
                    if val.startswith("-") or val.endswith("-"):
                        affix_parts.append(val)
                    elif " " not in val:
                        bases.append(val)
            # Last bare component is the base; earlier bare components are
            # part of the affix (e.g. "que" + "hacer" → affix="que", base="hacer").
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

        # ETY template with :af
        elif name == "ety" and args.get("1") == "es" and args.get("2") == ":af":
            affix_parts: list[str] = []
            bases: list[str] = []
            for key in sorted(args.keys()):
                if key in ("1", "2", "text", "tree", "nocap", "nocat"):
                    continue
                val = args[key]
                if val and isinstance(val, str):
                    val = re.sub(r'<[^>]*>', '', val)
                    if val.startswith("-") or val.endswith("-"):
                        affix_parts.append(val)
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

        # ETYMON ancestors
        elif name in _ETYMON_TEMPLATES or (name == "ety" and args.get("1") == "es"):
            _parse_etymon_template(name, args, etymons)

        # DOUBLET
        elif name in ("doublet", "dbt") and args.get("1") == "es":
            twin = args.get("2", "")
            if twin:
                doublets.append(twin)

    # Parse etymology_text tree with language detection
    tree_entries = _parse_etym_tree(etym_text)
    etymtree_ancestors.extend(tree_entries)

    return {
        "internal": internal,
        "etymons": etymons,
        "doublets": doublets,
        "etymtree_ancestors": etymtree_ancestors,
    }


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
            word = word.lstrip("*")
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
            word_part = parts[-1].lstrip("*")
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
