"""English-cognate side table — the ``englishRelatives`` card's data (Phase 3).

One streaming pass over the English kaikki edition writes ``english_cognate``,
a display-only table: one row per (English lemma word, cited Latin norm) for
every English lemma entry that cites a Latin-family etymon.

**Posture: strictly display-only.** The table never feeds family membership,
root keys, or any edge type — the same posture the ``etymon``/``derivation``
tables and ``norm_root`` already hold (pipeline/README).  The family builder
never reads it; the build runs it only after families are finalised.

**Join-side filters** (designed and measured in docs/COGNATES_FEASIBILITY.md —
option (b), the exact-norm + norm_root join, 95.0% strict on the
post-refinement 40-pair audit):

1. ``is_usable_ancestor`` — the pipeline's own candidate filter (no
   reconstructed forms, no junk chars, no leading/trailing hyphen, len >= 3).
2. Pure lowercase ASCII letters (``[a-z]{3,}``) — rejects ``testudin-``-style
   reconstructed stems, ``me(n)sa``, ``#latin``, ``cf.``, ``viꝫ``, etc.
3. Observed language-code leaks in the word slot (``grc``, ``peo``, ``ar``,
   ``akk``, ``gkm``, ``hin``, ``qed``, ``auc``, ``ett``) — ``dercat`` chains
   put ISO codes in the word slot.
4. ``_PREFIX_BLOCK`` — a closed set of Latin preposition/prefix words
   (``trans``, ``ante``, ``contra``, ``post``, ``pro``, ``per``, ``extra``,
   ``intra``, …).  Words whose *only* shared citation is a bare preposition
   are prefix-only relations, not root cognates; the audit's weak class
   (1,098 pairs, 2.5%) was dropped after measurement.
5. English bound-morpheme/phrase POS excluded (``suffix``, ``prefix``,
   ``phrase``, ``proverb``, …) — ``-fix``, ``post-``, ``vagina dentata`` are
   not card content (749 entries, 2.0%).

**Homograph gloss hygiene:** rows are stored per (word, norm), and the gloss
comes from the specific POS entry that cited that norm.  Merged homographs
(``peel`` the skin-verb < ``pilare`` vs ``peel`` the baker's shovel < ``pala``)
therefore display the gloss of the sense that actually matched.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

from pipeline.build import _strip_latin_prefix
from pipeline.etymology import is_usable_ancestor, parse_templates
from pipeline.extract import _classify_entry

# The table must never feed the graph: assert it is not one of the tables
# the family builder or the build's core machinery reads.
_CORE_TABLES = frozenset({"lemma", "form", "family", "etymon", "derivation"})
assert "english_cognate" not in _CORE_TABLES, (
    "english_cognate must stay a display-only side table"
)

# Latin-family codes the English side is allowed to cite (same family the
# Spanish side's etymon rows use, incl. the two extras our data carries).
_LA_RE = re.compile(r"^la(-lat|-med|-vul|-ecc|-new|-cla|-eme|-lit)?$")

# Language codes / abbreviations that leak into the word slot of dercat and
# chain templates (observed in the English edition); not Latin words.
_LANG_LEAKS = frozenset({"grc", "peo", "ar", "akk", "gkm", "hin",
                         "qed", "auc", "ett"})

_ASCII_LETTERS = re.compile(r"[a-z]{3,}$")

# Closed set of Latin preposition/prefix words (>= 3 chars; the 2-char ones
# like ex/de/ad already fail is_usable_ancestor).  A citation of one of these
# is usually a prefix component, not the root — the measured weak class.
_PREFIX_BLOCK = frozenset({
    "trans", "ante", "post", "contra", "extra", "intra", "ultra", "retro",
    "circum", "dis", "infra", "pro", "per", "prae", "pre", "super", "sub",
    "inter", "con", "com", "co", "af", "ef", "im", "sur", "tra", "bene",
    "male", "satis", "non", "semi", "bi", "tri", "quadri", "multi", "uni",
})

# English bound morphemes and multi-word phrases: never card content
# (mirrors the pipeline's _BOUND_POS family-membership exclusion).
_BOUND_POS = frozenset({
    "suffix", "prefix", "interfix", "infix",
    "phrase", "proverb", "prep_phrase", "adv_phrase",
    "character", "punct", "symbol",
})


def usable_norm(norm: str) -> bool:
    """Join-side norm filter — uniform on both sides of the join."""
    if not is_usable_ancestor(norm, "la"):
        return False
    if not _ASCII_LETTERS.match(norm):
        return False
    if norm in _LANG_LEAKS:
        return False
    if norm in _PREFIX_BLOCK:
        return False
    return True


def _first_gloss(entry: dict) -> str:
    for sense in entry.get("senses") or []:
        glosses = sense.get("glosses") or []
        if glosses:
            return glosses[0]
    return ""


def iter_rows(path: str | Path):
    """Stream the English edition; yield one dict per (word, norm) citation.

    Each dict: ``{word, pos, gloss, norm, norm_root}``.  Only lemma entries
    (pipeline classification) citing a usable Latin-family etymon.
    """
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            entry = json.loads(line)
            if _classify_entry(entry) != "lemma-entry":
                continue
            if entry.get("pos") in _BOUND_POS:
                continue
            templates = entry.get("etymology_templates") or []
            etym_text = " ".join(entry.get("etymology_texts") or [])
            parsed = parse_templates(entry.get("word", ""), templates, etym_text)
            norms: set[str] = set()
            for norm, lang, _mode, _src in parsed["etymons"]:
                if lang and _LA_RE.match(lang) and usable_norm(norm):
                    norms.add(norm)
            for norm, lang, _mode, _src, _ln in parsed["etymtree_raw"]:
                if lang and _LA_RE.match(lang) and usable_norm(norm):
                    norms.add(norm)
            if not norms:
                continue
            word = entry.get("word", "")
            gloss = _first_gloss(entry)
            pos = entry.get("pos", "")
            for norm in sorted(norms):
                yield {
                    "word": word,
                    "pos": pos,
                    "gloss": gloss,
                    "norm": norm,
                    "norm_root": _strip_latin_prefix(norm),
                }


def import_english_cognates(conn: sqlite3.Connection,
                            path: str | Path,
                            verbose: bool = True) -> int:
    """Create and fill ``english_cognate`` from the English edition.

    Additive-only: inserts into the new table, never into the core tables.
    One row per (word, norm); first record wins (keeps the gloss of the
    entry that cited the norm).  Returns the row count; 0 when the source
    file is absent (the API then renders the §52 empty state).
    """
    src = Path(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS english_cognate (
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL,
            pos TEXT NOT NULL,
            gloss TEXT,
            norm TEXT NOT NULL,      -- accent/macron-stripped Latin form — the join key
            norm_root TEXT NOT NULL  -- norm with at most one Latin prefix stripped
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS english_cognate_norm_idx "
        "ON english_cognate(norm)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS english_cognate_norm_root_idx "
        "ON english_cognate(norm_root)"
    )
    if not src.exists():
        print(f"[{_ts()}]   English edition not found at {src} — "
              f"english_cognate left empty (the card renders its empty state)")
        return 0
    t0 = time.time()
    seen: set[tuple[str, str]] = set()
    n_rows = 0
    n_words = set()
    n_norms = set()
    owns_tx = not conn.in_transaction
    if owns_tx:
        conn.execute("BEGIN")
    try:
        for row in iter_rows(src):
            key = (row["word"], row["norm"])
            if key in seen:
                continue
            seen.add(key)
            n_words.add(row["word"])
            n_norms.add(row["norm"])
            conn.execute(
                "INSERT INTO english_cognate (word, pos, gloss, norm, norm_root) "
                "VALUES (?, ?, ?, ?, ?)",
                (row["word"], row["pos"], row["gloss"],
                 row["norm"], row["norm_root"]),
            )
            n_rows += 1
        conn.execute(
            "INSERT INTO meta (k, v) VALUES ('n_english_cognates', ?)",
            (str(n_rows),),
        )
        conn.execute(
            "INSERT INTO meta (k, v) VALUES ('n_english_words', ?)",
            (str(len(n_words)),),
        )
        conn.execute(
            "INSERT INTO meta (k, v) VALUES ('n_english_norms', ?)",
            (str(len(n_norms)),),
        )
        if owns_tx:
            conn.execute("COMMIT")
    except BaseException:
        if owns_tx:
            conn.execute("ROLLBACK")
        raise
    if verbose:
        print(f"[{_ts()}]   {n_rows} english_cognate rows for {len(n_words)} "
              f"English words / {len(n_norms)} Latin norms "
              f"({time.time() - t0:.1f}s)")
    return n_rows


def _ts() -> str:
    return time.strftime("%H:%M:%S")
