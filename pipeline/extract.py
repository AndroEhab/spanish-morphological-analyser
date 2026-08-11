"""Pass 1: stream JSONL -> classify entries, emit form links and lemma records."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pipeline.normalize import build_key, fold

_SKIP_POS = frozenset({"character", "punct", "symbol", "interfix", "infix"})


def _has_form_of(sense: dict) -> bool:
    tags = sense.get("tags") or []
    return "form-of" in tags or "alt-of" in tags


def _is_misspelling(sense: dict) -> bool:
    tags = sense.get("tags") or []
    return "alt-of" in tags and "misspelling" in tags


def _extract_gloss(senses: list[dict]) -> str | None:
    for sense in senses:
        if _has_form_of(sense):
            continue
        raw = sense.get("raw_glosses") or sense.get("glosses") or []
        if raw:
            gloss = raw[0]
            gloss = re.sub(r"^\([^)]*\)\s*", "", gloss).strip()
            if gloss:
                return gloss
    return None


def _extract_gloss_tail(sense: dict) -> str | None:
    glosses = sense.get("glosses") or []
    if not glosses:
        return None
    if len(glosses) >= 2:
        return glosses[1]
    return glosses[0]


def _classify_entry(entry: dict) -> str:
    pos = entry.get("pos", "")
    if pos in _SKIP_POS:
        return "skip"
    senses = entry.get("senses") or []
    if not senses:
        return "lemma-entry"
    has_form_of = False
    has_non_form_of = False
    all_misspelling = True
    for sense in senses:
        if _has_form_of(sense):
            has_form_of = True
            if not _is_misspelling(sense):
                all_misspelling = False
        else:
            has_non_form_of = True
    if has_form_of and not has_non_form_of:
        if all_misspelling:
            return "skip"
        return "form-entry"
    return "lemma-entry"


def _filter_forms(forms: list[dict]) -> list[dict]:
    out = []
    for f in forms:
        tags = f.get("tags") or []
        if "table-tags" in tags or "inflection-template" in tags or "error-unrecognized-form" in tags:
            continue
        out.append({"form": f["form"], "tags": list(tags)})
    return out


def _extract_gender(entry: dict) -> str:
    """Citation gender from the head template: 'masculine', 'feminine', or ''.

    Spanish noun templates encode gender as arg 1 ('m'/'f'); adjectives and
    gender-agnostic templates leave it unknown.
    """
    for ht in entry.get("head_templates") or []:
        args = ht.get("args") or {}
        g = args.get("1")
        if g in ("m", "m-s"):
            return "masculine"
        if g in ("f", "f-s"):
            return "feminine"
    return ""


def _extract_derived_related(entry: dict) -> tuple[list[str], list[str]]:
    """Return (derived_words, related_words) as separate lists."""
    derived: set[str] = set()
    related: set[str] = set()
    for key in ("derived", "related"):
        target = derived if key == "derived" else related
        for item in entry.get(key) or []:
            w = item.get("word", "")
            if w and " " not in w:
                target.add(w)
    for sense in entry.get("senses") or []:
        for key in ("derived", "related"):
            target = derived if key == "derived" else related
            for item in sense.get(key) or []:
                w = item.get("word", "")
                if w and " " not in w:
                    target.add(w)
    return sorted(derived), sorted(related)


def extract(jsonl_path: str | Path, output_dir: str | Path) -> tuple[int, int, int]:
    jsonl_path = Path(jsonl_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lemmas_fh = open(output_dir / "lemmas.jsonl", "w", encoding="utf-8")
    links_fh = open(output_dir / "form_links.jsonl", "w", encoding="utf-8")

    n_lemmas = 0
    n_links = 0
    lemma_id_counter = 1

    # Fast lookup: folded_word -> list of (lemma_id, pos, has_forms)
    lemma_by_word: dict[str, list[dict]] = {}

    print("  Streaming JSONL...")
    with open(jsonl_path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i % 100000 == 0 and i > 0:
                print(f"    {i} lines...")
            line = line.strip()
            if not line:
                continue

            entry = json.loads(line)
            classification = _classify_entry(entry)

            if classification == "skip":
                continue

            word = entry.get("word", "")
            pos = entry.get("pos", "")

            if classification == "form-entry":
                senses = entry.get("senses") or []
                for sense in senses:
                    if not _has_form_of(sense) or _is_misspelling(sense):
                        continue
                    form_of = sense.get("form_of") or []
                    if not form_of:
                        continue
                    lemma_word = form_of[0].get("word", "")
                    tags = [t for t in (sense.get("tags") or []) if t != "form-of"]
                    gloss_tail = _extract_gloss_tail(sense)
                    link = {
                        "surface": word,
                        "surface_key": build_key(word),
                        "pos": pos,
                        "lemma_word": lemma_word,
                        "tags": tags,
                        "gloss_tail": gloss_tail,
                    }
                    links_fh.write(json.dumps(link, ensure_ascii=False) + "\n")
                    n_links += 1
            else:
                etym_no = _get_etymology_number(entry)
                gloss = _extract_gloss(entry.get("senses") or [])
                head_templates = entry.get("head_templates") or []
                head_expansion = head_templates[0].get("expansion", "") if head_templates else ""
                filtered_forms = _filter_forms(entry.get("forms") or [])
                etym_text = entry.get("etymology_text", "")
                derived_words, related_words = _extract_derived_related(entry)
                etym_templates = entry.get("etymology_templates") or []

                lemma_id = lemma_id_counter
                lemma_id_counter += 1

                lemma_record = {
                    "id": lemma_id, "word": word, "pos": pos,
                    "etym_no": etym_no, "gloss": gloss,
                    "head_expansion": head_expansion,
                    "gender": _extract_gender(entry),
                    "forms": filtered_forms,
                    "derived": derived_words,
                    "related": related_words,
                    "etymology_text": etym_text,
                    "etymology_templates": json.dumps(etym_templates, ensure_ascii=False),
                }
                lemmas_fh.write(json.dumps(lemma_record, ensure_ascii=False) + "\n")
                n_lemmas += 1

                folded = fold(word)
                if folded not in lemma_by_word:
                    lemma_by_word[folded] = []
                lemma_by_word[folded].append({
                    "id": lemma_id, "pos": pos,
                    "etym_no": etym_no, "has_forms": bool(filtered_forms),
                })

    lemmas_fh.close()
    links_fh.close()

    print(f"  {n_lemmas} lemmas, {n_links} form links")
    print("  Resolving form links...")

    # Second pass: resolve links with fast O(1) lookup
    n_forms = 0
    with open(output_dir / "form_links.jsonl", encoding="utf-8") as fh, \
         open(output_dir / "forms.jsonl", "w", encoding="utf-8") as out:
        for i, line in enumerate(fh):
            if i % 100000 == 0 and i > 0:
                print(f"    {i} links resolved...")
            line = line.strip()
            if not line:
                continue
            link = json.loads(line)
            lemma_word = link["lemma_word"]
            pos = link["pos"]
            folded_lw = fold(lemma_word)

            lemma_id = _resolve_lemma_fast(folded_lw, pos, lemma_by_word)
            if lemma_id is None:
                # The form_of target has no lemma entry (alt-of/obsolete
                # spelling, cross-language, or multiword junk). Drop the
                # row instead of minting an orphan that points nowhere.
                continue

            form_record = {
                "form": link["surface"],
                "key": link["surface_key"],
                "lemma_id": lemma_id,
                "features": link["tags"],
                "is_lemma": 0,
                "is_clitic": 1 if "combined-form" in link["tags"] else 0,
                "freq": 0.0,
            }
            out.write(json.dumps(form_record, ensure_ascii=False) + "\n")
            n_forms += 1

    print(f"  {n_forms} form records")
    return n_lemmas, n_forms, n_links
def _get_etymology_number(entry: dict) -> int:
    en = entry.get("etymology_number")
    if en is None:
        return 0
    try:
        return int(en)
    except (ValueError, TypeError):
        return 0


def _resolve_lemma_fast(
    folded_lemma: str, pos: str,
    lemma_by_word: dict[str, list[dict]],
) -> int | None:
    """Best-matching lemma id for a form link; None when the target has no
    lemma entry (alt-of/obsolete spellings, cross-language, multiword)."""
    entries = lemma_by_word.get(folded_lemma)
    if not entries:
        return None

    # Prefer same pos, then one with forms, then lowest etym_no
    same_pos = [e for e in entries if e["pos"] == pos]
    if same_pos:
        with_forms = [e for e in same_pos if e["has_forms"]]
        if with_forms:
            return with_forms[0]["id"]
        return same_pos[0]["id"]

    # Any pos
    with_forms = [e for e in entries if e["has_forms"]]
    if with_forms:
        return with_forms[0]["id"]
    return entries[0]["id"]
