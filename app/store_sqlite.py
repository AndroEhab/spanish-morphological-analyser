"""SQLite-backed data access for the morphological analyser.

Search/analyze/health contract identical to the fixture backend
(``app/store_fixture.py``), hardened for real-data volume:

- Ranking: tier 0 exact folded-key match, tier 1 prefix, tier 2 substring.
  Tiers 0+1 come from one indexed range scan (``key >= q AND key < q_upper``,
  no LIKE); the substring scan runs only when the prefix path finds nothing,
  requires a query of at least 3 folded characters, and is capped at 200.
  Within a tier: frequency desc, then form length asc, then form asc, then
  lemma asc — byte-identical ordering to the fixture backend.
- Rows for the same surface form (homographs / homonymous analyses) stay
  adjacent and survive the ``limit`` cut as a whole group or not at all.
- Ambiguity (the ``qualifier``) is computed over distinct ``lemma_id``, not
  distinct lemma words, so same-word homographs (e.g. haz "bundle" vs haz
  "face") still get a qualifier and remain distinguishable by gloss/POS.
- One read-only thread-local connection per thread (FastAPI runs sync
  handlers in a threadpool); ``PRAGMA query_only=ON``; the schema is
  validated lazily and the file is re-checked per call so the store fails
  with a clear error (not a crash) if the DB is missing or mid-rebuild.

The database is rebuilt by the pipeline worker; this module must survive
data changing underneath it, so it never caches row counts or tunes to
specific data. ``MORPH_SQLITE_PATH`` overrides the database location
(used by the tests; unset in production).
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from threading import local

import orjson

from pipeline.normalize import fold as _fold

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "morph.sqlite"
_DB_PATH = Path(os.environ.get("MORPH_SQLITE_PATH") or _DEFAULT_DB)

_REQUIRED_TABLES = ("form", "lemma", "family", "meta")

# Performance guardrails (documented in the module docstring).
_SUBSTRING_MIN_LEN = 3
_SUBSTRING_CAP = 200
_PREFIX_OVERFETCH = 500  # enough headroom for the whole-group limit rule

# POS group order for the family view: verb, noun, adj, adv, then the rest
# alphabetically by plural label. Empty groups are omitted by the backend.
_GROUP_ORDER = ["verb", "noun", "adj", "adv"]

_POS_LABELS = {
    "verb": "Verbs",
    "noun": "Nouns",
    "adj": "Adjectives",
    "name": "Names",
    "adv": "Adverbs",
    "suffix": "Suffixes",
    "phrase": "Phrases",
    "intj": "Interjections",
    "prefix": "Prefixes",
    "pron": "Pronouns",
    "prep": "Prepositions",
    "num": "Numerals",
    "proverb": "Proverbs",
    "conj": "Conjunctions",
    "det": "Determiners",
    "character": "Characters",
    "prep_phrase": "Prepositional phrases",
    "contraction": "Contractions",
    "symbol": "Symbols",
    "article": "Articles",
    "particle": "Particles",
    "punct": "Punctuation",
    "interfix": "Interfixes",
    "infix": "Infixes",
    "adv_phrase": "Adverbial phrases",
}


def _pos_label(pos: str) -> str:
    return _POS_LABELS.get(pos, f"{pos}s".capitalize())


# Canonical grammatical ordering for a member's forms, derived from the
# first feature string. Unknown tenses sort last (rank 100), ties broken by
# the form itself (alphabetical) — see _form_sort_key.
_TENSE_ORDER = {
    "infinitive": 0,
    "gerund": 1,
    "participle": 2,
    "present": 8,            # short form, e.g. "present, 1st singular"
    "preterite": 9,
    "present indicative": 10,
    "imperfect indicative": 11,
    "preterite indicative": 12,
    "future indicative": 13,
    "conditional indicative": 14,
    "present subjunctive": 20,
    "imperfect subjunctive": 21,
    "future subjunctive": 22,
    "imperative": 30,
    "singular": 40,          # noun/adjective number/gender features
    "plural": 41,
    "masculine": 42,
    "feminine": 43,
    "alternative": 50,
    "canonical": 51,
    "class": 52,
    "superlative": 53,
    "diminutive": 54,
    "demonym": 55,
}

_SELECT_FORM = """
SELECT f.id, f.form, f.key, f.lemma_id, f.features, f.is_lemma, f.is_clitic, f.freq,
       l.word AS lemma, l.pos, l.gloss, l.family_id
FROM form f JOIN lemma l ON f.lemma_id = l.id
"""


class StoreError(RuntimeError):
    """The SQLite store is unavailable (missing file or incomplete schema)."""


_thread = local()


def _connect() -> sqlite3.Connection:
    """One read-only thread-local connection; fails with a clear error."""
    if not _DB_PATH.exists():
        raise StoreError(
            f"SQLite database not found at {_DB_PATH} — the pipeline may not have built it yet"
        )
    conn = getattr(_thread, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        # The pipeline rebuilds the database in place; wait out writer locks
        # instead of failing mid-keystroke (WAL reads still see a snapshot).
        conn.execute("PRAGMA busy_timeout=15000")
        _thread.conn = conn
        _thread.schema_checked = False
    if not getattr(_thread, "schema_checked", False):
        present = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [t for t in _REQUIRED_TABLES if t not in present]
        if missing:
            raise StoreError(
                f"SQLite schema incomplete (missing table(s): {', '.join(missing)}) — "
                "the pipeline may still be building the database"
            )
        _thread.schema_checked = True
    return conn


def _upper_bound(q: str) -> str:
    """Exclusive upper bound for a prefix range: increment the last char."""
    return q[:-1] + chr(ord(q[-1]) + 1)


def _parse_features(features_raw) -> list[str]:
    if not features_raw:
        return []
    try:
        # orjson is several times faster than json.loads; the pipeline emits
        # JSON arrays, which is the hot path for large families.
        parsed = orjson.loads(features_raw)
    except (orjson.JSONDecodeError, TypeError):
        return []
    if isinstance(parsed, list):
        return [str(f) for f in parsed]
    return [str(parsed)]


def _merged(rows) -> dict:
    """Merge sqlite rows sharing (form, lemma_id) into one row.

    The pipeline can emit the same surface form under one lemma as several
    rows carrying complementary feature analyses (homonymous forms such as
    'mienta' = 1st/3rd present subjunctive). The merged features are the
    ordered union; the representative id is the highest-freq row (ties:
    lowest id); is_lemma is set if any row is the citation form.
    """
    best = max(rows, key=lambda r: (r["freq"], -r["id"]))
    features: list[str] = []
    seen: set[str] = set()
    for r in sorted(rows, key=lambda r: r["id"]):
        for feat in _parse_features(r["features"]):
            if feat not in seen:
                seen.add(feat)
                features.append(feat)
    merged = dict(best)
    merged["features"] = features
    merged["is_lemma"] = any(bool(r["is_lemma"]) for r in rows)
    return merged


def _group_merged(raw, tier: int) -> list[dict]:
    groups: dict[tuple[str, int], list] = {}
    for r in raw:
        groups.setdefault((r["form"], r["lemma_id"]), []).append(r)
    out = []
    for rows in groups.values():
        m = _merged(rows)
        m["tier"] = tier
        out.append(m)
    return out


def _row_sort_key(r: dict) -> tuple:
    return (-r["freq"], len(r["form"]), r["form"], r["lemma"])


def _sort_and_cut(merged: list[dict], limit: int) -> list[dict]:
    """Sort byte-identically to the fixture backend, then apply the limit on
    whole surface-form groups.

    Groups of rows sharing one surface form are ordered by (tier, best group
    frequency desc, form length asc, form asc); within a group rows are
    ordered by (freq desc, form length asc, form asc, lemma asc). The limit
    includes a group entirely or drops it entirely — never splits it.
    """
    groups: dict[str, list[dict]] = {}
    for r in merged:
        groups.setdefault(r["form"], []).append(r)

    def group_key(item: tuple[str, list[dict]]) -> tuple:
        form, rows = item
        # Single-word forms sort before multi-word ones within the same tier:
        # this is a word search, and kaikki multi-word entries (e.g.
        # "hacer popó") must not crowd out the paradigm for short prefixes.
        return (rows[0]["tier"], " " in form, -max(r["freq"] for r in rows), len(form), form)

    selected: list[dict] = []
    remaining = limit
    for form, rows in sorted(groups.items(), key=group_key):
        rows.sort(key=_row_sort_key)
        if len(rows) <= remaining:
            selected.extend(rows)
            remaining -= len(rows)
        else:
            break
    return selected


def _search_row(r: dict) -> dict:
    return {
        "id": str(r["id"]),
        "form": r["form"],
        "lemma": r["lemma"],
        "pos": r["pos"],
        "label": r["form"],
        "gloss": r["gloss"] or "",
        "freq": r["freq"],
        "is_lemma": bool(r["is_lemma"]),
        "features": r["features"],
        "qualifier": r.get("qualifier"),
    }


def _apply_qualifiers(rows: list[dict]) -> list[dict]:
    """Set ``qualifier`` (the row's own lemma word) on rows whose surface
    form maps to more than one distinct lemma_id among the returned rows."""
    per_form: dict[str, set[int]] = {}
    for r in rows:
        per_form.setdefault(r["form"], set()).add(r["lemma_id"])
    ambiguous = {form for form, ids in per_form.items() if len(ids) > 1}
    out = []
    for r in rows:
        out.append({**r, "qualifier": r["lemma"] if r["form"] in ambiguous else None})
    return out


def _fetch_top_ids(conn: sqlite3.Connection, where: str, args: tuple, cap: int) -> list[int]:
    """Top-``cap`` form ids for a key predicate.

    Fetching the ids via the covering ``form_key_freq_idx`` first keeps
    SQLite's top-N sorter optimization intact: ``ORDER BY freq DESC`` joined
    against ``lemma`` in one statement makes the planner materialize the
    whole range (250ms+ for a 250k-row prefix like ``a*``), while the
    id-only query stays at ~25ms.
    """
    return [
        r["id"]
        for r in conn.execute(
            f"SELECT f.id FROM form f WHERE {where} ORDER BY f.freq DESC LIMIT ?",
            (*args, cap),
        )
    ]


def _fetch_by_ids(conn: sqlite3.Connection, ids: list[int]) -> list:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    return list(conn.execute(_SELECT_FORM + f"WHERE f.id IN ({placeholders})", ids))


def search(q: str, limit: int) -> list[dict]:
    """Tiered search: exact, then prefix, then (sparingly) substring.

    Tiers 0 and 1 come from one indexed range scan over ``form.key``; the
    substring scan (full key scan, expensive) runs only when the prefix path
    found nothing and the query is at least ``_SUBSTRING_MIN_LEN`` chars.
    """
    q = q.strip()
    if not q:
        return []
    folded = _fold(q)
    if not folded:  # e.g. a lone accent mark folds to nothing
        return []
    conn = _connect()

    exact = list(conn.execute(_SELECT_FORM + "WHERE f.key = ? ORDER BY f.id", (folded,)))
    prefix = _fetch_by_ids(
        conn,
        _fetch_top_ids(
            conn, "f.key > ? AND f.key < ?", (folded, _upper_bound(folded)), _PREFIX_OVERFETCH
        ),
    )
    raw_tier2 = []
    if not exact and not prefix and len(folded) >= _SUBSTRING_MIN_LEN:
        raw_tier2 = _fetch_by_ids(
            conn,
            _fetch_top_ids(
                conn, "f.key LIKE '%' || ? || '%'", (folded,), _SUBSTRING_CAP
            ),
        )

    merged = _group_merged(exact, 0) + _group_merged(prefix, 1) + _group_merged(raw_tier2, 2)
    selected = _sort_and_cut(merged, limit)
    return [_search_row(r) for r in _apply_qualifiers(selected)]


def _relation_label_fallback(relation: str, head_word: str) -> str:
    if relation == "root":
        return "root"
    if relation == "paradigm":
        return f"same paradigm as {head_word}"
    if relation == "derived":
        return f"related to {head_word}"
    if relation in ("inherited", "affix"):
        return relation
    return ""


def _form_sort_key(m: dict) -> tuple:
    """Citation first, then non-clitic forms, then clitic forms; within each
    block a canonical grammatical order derived from the features, else
    alphabetical by form."""
    feats = m["features"] or [""]
    head = feats[0].partition(",")[0].strip()
    tense = _TENSE_ORDER.get(head, 100)
    if tense == 100:
        if head.startswith("infinitive +"):
            tense = 70
        elif head.startswith("gerund +"):
            tense = 71
        elif head.startswith("imperative +"):
            tense = 72
    rest = feats[0].partition(",")[2].strip()
    if rest:
        num = 1 if "1st" in rest else 2 if "2nd" in rest else 3 if "3rd" in rest else 0
        person = num + (3 if "plural" in rest else 0) if num else 7
    else:
        person = 7
    return (0 if m["is_lemma"] else 1, bool(m["is_clitic"]), tense, person, m["form"])


def _member_forms_map(conn: sqlite3.Connection, lemma_ids: list[int]) -> dict[int, list[dict]]:
    """All member forms in one indexed query, merged per (lemma_id, form).

    With N+1 per-member queries a large family (thousands of members) would
    take seconds; a single ``lemma_id IN (...)`` scan over ``form_lemma_idx``
    keeps it linear in the number of forms.
    """
    by_lemma: dict[int, list[dict]] = {lid: [] for lid in lemma_ids}
    if not lemma_ids:
        return by_lemma
    placeholders = ",".join("?" * len(lemma_ids))
    raw = conn.execute(
        f"SELECT lemma_id, id, form, features, is_lemma, is_clitic, freq "
        f"FROM form WHERE lemma_id IN ({placeholders}) ORDER BY lemma_id, id",
        lemma_ids,
    ).fetchall()
    for r in raw:
        by_lemma[r["lemma_id"]].append(r)
    out: dict[int, list[dict]] = {}
    for lid, rows in by_lemma.items():
        groups: dict[str, list] = {}
        for r in rows:
            groups.setdefault(r["form"], []).append(r)
        merged = [_merged(groups[form]) for form in groups]
        merged.sort(key=_form_sort_key)
        out[lid] = [
            {
                "form": m["form"],
                "features": " \u00b7 ".join(m["features"]) if m["features"] else "",
                "is_lemma": bool(m["is_lemma"]),
            }
            for m in merged
        ]
    return out


def _member_view(m, head_word: str, head_id: int, forms: list[dict]) -> dict:
    relation = m["relation"] or ""
    relation_label = (m["relation_label"] or "").strip()
    if not relation_label:
        relation_label = _relation_label_fallback(relation, head_word)
    return {
        "lemma": m["word"],
        "gloss": m["gloss"] or "",
        "relation": relation,
        "relation_label": relation_label,
        "is_head": m["id"] == head_id,
        "forms": forms,
    }


def analyze(entry_id: str) -> dict | None:
    """Family view for one form entry id; ``None`` -> 404."""
    try:
        form_id = int(entry_id)
    except (ValueError, TypeError):
        return None

    conn = _connect()
    row = conn.execute(_SELECT_FORM + "WHERE f.id = ?", (form_id,)).fetchone()
    if row is None:
        return None

    family_id = row["family_id"]
    if family_id is None:
        return None

    fam = conn.execute(
        "SELECT id, head_lemma_id, note FROM family WHERE id = ?", (family_id,)
    ).fetchone()
    if fam is None:
        return None

    head = conn.execute(
        "SELECT id, word, pos, gloss FROM lemma WHERE id = ?", (fam["head_lemma_id"],)
    ).fetchone()
    if head is None:
        return None

    # The selected block mirrors the search row: same surface form and lemma,
    # with every analysis merged (homonymous forms are split across rows).
    same_form = conn.execute(
        _SELECT_FORM + "WHERE f.form = ? AND f.lemma_id = ? ORDER BY f.id",
        (row["form"], row["lemma_id"]),
    ).fetchall()
    selected_row = _merged(same_form)
    selected = {
        "id": str(form_id),
        "form": selected_row["form"],
        "lemma": selected_row["lemma"],
        "pos": selected_row["pos"],
        "gloss": selected_row["gloss"] or "",
        "features": selected_row["features"],
    }

    members = conn.execute(
        "SELECT id, word, pos, gloss, freq, relation, relation_label FROM lemma "
        "WHERE family_id = ?",
        (family_id,),
    ).fetchall()
    head_id = fam["head_lemma_id"]
    members_sorted = sorted(members, key=lambda m: (m["id"] != head_id, -m["freq"], m["word"]))

    forms_map = _member_forms_map(conn, [m["id"] for m in members_sorted])

    by_pos: dict[str, list[dict]] = {}
    for m in members_sorted:
        by_pos.setdefault(m["pos"], []).append(
            _member_view(m, head["word"], head_id, forms_map[m["id"]])
        )

    extra = sorted((pos for pos in by_pos if pos not in _GROUP_ORDER), key=_pos_label)
    group_order = [pos for pos in _GROUP_ORDER + extra if pos in by_pos]

    groups = [
        {"pos": pos, "pos_label": _pos_label(pos), "members": by_pos[pos]}
        for pos in group_order
    ]

    return {
        "selected": selected,
        "family": {
            "head": {
                "lemma": head["word"],
                "pos": head["pos"],
                "gloss": head["gloss"] or "",
            },
            "note": fam["note"],
            "groups": groups,
        },
    }


def health() -> dict:
    """Health stats from the ``meta`` table (no COUNT(*) over 1.2M rows)."""
    conn = _connect()
    try:
        meta = {r["k"]: r["v"] for r in conn.execute("SELECT k, v FROM meta")}

        def _count(meta_key: str, table: str) -> int:
            if meta_key in meta:
                try:
                    return int(meta[meta_key])
                except (TypeError, ValueError):
                    pass
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        return {
            "status": "ok",
            "backend": "sqlite",
            "entries": _count("n_forms", "form"),
            "lemmas": _count("n_lemmas", "lemma"),
            "families": _count("n_families", "family"),
        }
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        raise StoreError(f"SQLite store unavailable: {exc}") from exc
