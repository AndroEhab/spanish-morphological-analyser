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

# Ancestry / cousins feature: proto-language codes are never join keys.
_PROTO_LANGS = frozenset({
    "ine-pro", "itc-pro", "gem-pro", "cel-pro", "grk-pro",
    "sla-pro", "bat-pro", "ine", "qfa-sub", "sem-pro", "afa-pro",
})
_ANCESTRY_CAP = 8          # ancestry entries including the Spanish word itself
_COUSIN_FANOUT_CAP = 60    # shared etymon with more descendants is too generic
_COUSIN_NOTE = "Descended from the same ancestor, but outside this word's family under the paradigm cutoff."


def _is_proto(lang: str) -> bool:
    return lang in _PROTO_LANGS or lang.endswith("-pro")


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        is not None
    )

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


def _family_tree(
    conn: sqlite3.Connection,
    head_id: int,
    members: list,
    forms_map: dict[int, list[dict]],
    selected_lemma_id: int,
    has_derivation: bool,
) -> dict:
    """The family's derivation tree, depth-first, parent before child.

    Parent pointers come from the ``derivation`` table (the BFS tree the
    pipeline persisted).  A member with no derivation row (root-key /
    homograph sibling without a derivational parent) attaches to the head
    with its own relation at depth 1 — never orphaned.
    """
    parent_of: dict[int, int] = {}
    if has_derivation:
        ids = [m["id"] for m in members]
        placeholders = ",".join("?" * len(ids))
        for r in conn.execute(
            f"SELECT child_id, parent_id FROM derivation WHERE child_id IN ({placeholders})",
            ids,
        ):
            parent_of[r["child_id"]] = r["parent_id"]

    children: dict[int, list[int]] = {}
    for m in members:
        if m["id"] == head_id:
            continue
        pid = parent_of.get(m["id"], head_id)
        children.setdefault(pid, []).append(m["id"])
    by_id = {m["id"]: m for m in members}
    # Stable sibling order: the family's canonical sort_key (head first,
    # then relation priority, then word) is stored on each lemma.
    for pid in children:
        children[pid].sort(key=lambda lid: (by_id[lid]["sort_key"], lid))

    nodes: list[dict] = []
    stack = [(head_id, 0)]
    head_word = by_id[head_id]["word"]
    while stack:
        lid, depth = stack.pop()
        m = by_id[lid]
        relation = m["relation"] or ("root" if lid == head_id else "")
        label = (m["relation_label"] or "").strip() or _relation_label_fallback(relation, head_word)
        if lid == head_id:
            relation, label = "root", "root"
        nodes.append({
            "lemma_id": lid,
            "lemma": m["word"],
            "pos": m["pos"],
            "gloss": m["gloss"] or "",
            "parent_id": None if lid == head_id else parent_of.get(lid, head_id),
            "relation": relation,
            "label": label,
            "depth": depth,
            "freq": m["freq"],
            "form_count": len(forms_map.get(lid, [])),
            "is_selected": lid == selected_lemma_id,
        })
        # depth-first: push children reversed so they pop in sorted order
        for child in reversed(children.get(lid, ())):
            stack.append((child, depth + 1))
    return {
        "root_lemma_id": head_id,
        "nodes": nodes,
    }


def _ancestry_for(conn: sqlite3.Connection, lemma_id: int, lemma_word: str, has_etymon: bool) -> list[dict]:
    """Ancestry chain: the Spanish word itself, then its parsed etymons,
    most recent first.  At most one proto-language link is shown (PIE roots
    are noise beyond the first); the whole array is capped at 8 entries."""
    if not has_etymon:
        return []
    rows = conn.execute(
        "SELECT depth, lang, lang_label, word, mode, note FROM etymon "
        "WHERE lemma_id = ? ORDER BY depth",
        (lemma_id,),
    ).fetchall()
    if not rows:
        return []
    entries: list[dict] = [{
        "lang": "es",
        "lang_label": "Spanish",
        "word": lemma_word,
        "mode": None,
        "note": None,
        "proto": False,
    }]
    proto_shown = False
    for r in rows:
        lang = r["lang"] or ""
        is_proto = lang and _is_proto(lang)
        if is_proto:
            if proto_shown:
                continue
            proto_shown = True
        entries.append({
            "lang": lang,
            "lang_label": r["lang_label"],
            "word": r["word"],
            "mode": r["mode"] or None,
            "note": r["note"],
            "proto": bool(is_proto),
        })
        if len(entries) >= _ANCESTRY_CAP:
            break
    return entries


def _cousin_fanout(conn: sqlite3.Connection, column: str, value: str) -> int:
    """Distinct lemmas citing ``value`` in ``column`` (non-proto, known lang)."""
    placeholders = ",".join("?" * len(_PROTO_LANGS))
    return conn.execute(
        f"SELECT COUNT(DISTINCT lemma_id) FROM etymon "
        f"WHERE {column} = ? AND lang != '' "
        f"AND lang NOT IN ({placeholders}) AND lang NOT LIKE '%-pro'",
        (value, *_PROTO_LANGS),
    ).fetchone()[0]


def _cousin_members(
    conn: sqlite3.Connection,
    column: str,
    value: str,
    family_id: int,
    exclude_id: int,
) -> list:
    """Lemmas sharing the etymon ``value``, outside ``family_id``.

    A lemma that is already a family member is never offered as a cousin —
    it would make the cousins strip and the family view contradict each
    other.  The selected lemma itself is always excluded too.
    """
    placeholders = ",".join("?" * len(_PROTO_LANGS))
    return conn.execute(
        "SELECT DISTINCT l.id, l.word, l.pos, l.gloss, l.freq, l.family_id "
        "FROM etymon e JOIN lemma l ON l.id = e.lemma_id "
        f"WHERE e.{column} = ? AND e.lang != '' "
        f"AND e.lang NOT IN ({placeholders}) AND e.lang NOT LIKE '%-pro' "
        "AND l.family_id != ? AND l.id != ? "
        "ORDER BY l.freq DESC, l.word ASC, l.id",
        (value, *_PROTO_LANGS, family_id, exclude_id),
    ).fetchall()


def _cousin_path(
    conn: sqlite3.Connection,
    member_id: int,
    shared: str,
    root_word: str,
    via_root: bool,
) -> str:
    """The member's chain down to the shared etymon.

    Exact-norm match: "iacto < iactāre".  Root match: the member's cited
    form is a prefixed reflex of the shared root, so the path states the
    decomposition — "obiectāre < ob- + iectāre" — or the plain chain when
    the member itself cites the root ("iecto < iectāre").
    """
    chain = conn.execute(
        "SELECT depth, lang, word, norm, norm_root FROM etymon "
        "WHERE lemma_id = ? ORDER BY depth",
        (member_id,),
    ).fetchall()
    if not via_root:
        for i, c in enumerate(chain):
            if c["norm"] == shared and (c["lang"] or "") and not _is_proto(c["lang"] or ""):
                return " < ".join(row["word"] for row in chain[: i + 1])
        return root_word
    # root match: prefer the deepest row whose root is the shared one
    hit = None
    hit_idx = -1
    for i, c in enumerate(chain):
        if (c["norm_root"] or c["norm"]) == shared and (c["lang"] or "") and not _is_proto(c["lang"] or ""):
            hit, hit_idx = c, i
    if hit is None:
        return root_word
    if hit["norm"] == shared:
        return " < ".join(row["word"] for row in chain[: hit_idx + 1])
    prefix = hit["norm"][: len(hit["norm"]) - len(shared)]
    if prefix:
        return f"{hit['word']} < {prefix}- + {root_word}"
    return f"{hit['word']} < {root_word}"


def _cousins_for(
    conn: sqlite3.Connection,
    lemma_id: int,
    family_id: int,
    has_etymon: bool,
) -> dict | None:
    """Lemmas sharing this word's deepest usable non-proto etymon.

    Joins on the exact ``norm`` first (strongest signal); when that yields
    nothing usable, falls back to ``norm_root`` — the norm with at most one
    Latin prefix stripped, which connects prefixed reflexes (obiectāre,
    proiectāre, iniectāre, subiectāre, disiectāre → iectāre).  Family
    members are never cousins, whatever the join.  An etymon with more
    than ``_COUSIN_FANOUT_CAP`` Spanish descendants is too generic: drop
    to the next-deepest etymon; if none qualifies (or no other lemma
    shares it) return None.
    """
    if not has_etymon:
        return None
    rows = conn.execute(
        "SELECT depth, lang, lang_label, word, norm, mode, norm_root FROM etymon "
        "WHERE lemma_id = ? ORDER BY depth DESC",
        (lemma_id,),
    ).fetchall()
    for cand in rows:
        lang = cand["lang"] or ""
        if not lang or _is_proto(lang):
            continue
        # 1) exact shared etymon — the strongest signal
        fanout = _cousin_fanout(conn, "norm", cand["norm"])
        if 1 < fanout <= _COUSIN_FANOUT_CAP:
            members = _cousin_members(conn, "norm", cand["norm"], family_id, lemma_id)
            if members:
                return {
                    "shared_etymon": {
                        "lang_label": cand["lang_label"],
                        "word": cand["word"],
                        "norm": cand["norm"],
                    },
                    "note": _COUSIN_NOTE,
                    "members": [
                        _cousin_member(conn, m, cand["norm"], cand["word"], via_root=False)
                        for m in members
                    ],
                }
        # 2) prefix-stripped root (prefixed reflexes of the same root)
        root = cand["norm_root"] or cand["norm"]
        fanout_root = _cousin_fanout(conn, "norm_root", root)
        if 1 < fanout_root <= _COUSIN_FANOUT_CAP:
            members = _cousin_members(conn, "norm_root", root, family_id, lemma_id)
            if members:
                placeholders = ",".join("?" * len(_PROTO_LANGS))
                root_row = conn.execute(
                    f"SELECT word, lang_label FROM etymon WHERE norm = ? AND lang != '' "
                    f"AND lang NOT IN ({placeholders}) AND lang NOT LIKE '%-pro' "
                    "ORDER BY lemma_id, depth LIMIT 1",
                    (root, *_PROTO_LANGS),
                ).fetchone()
                root_word = root_row["word"] if root_row else cand["word"]
                root_label = root_row["lang_label"] if root_row else cand["lang_label"]
                return {
                    "shared_etymon": {
                        "lang_label": root_label,
                        "word": root_word,
                        "norm": root,
                    },
                    "note": _COUSIN_NOTE,
                    "members": [
                        _cousin_member(conn, m, root, root_word, via_root=True)
                        for m in members
                    ],
                }
    return None


def _cousin_member(
    conn: sqlite3.Connection,
    m,
    shared: str,
    root_word: str,
    via_root: bool,
) -> dict:
    path = _cousin_path(conn, m["id"], shared, root_word, via_root)
    head_row = conn.execute(
        "SELECT l.word FROM family f JOIN lemma l ON l.id = f.head_lemma_id "
        "WHERE f.id = ?",
        (m["family_id"],),
    ).fetchone()
    entry_row = conn.execute(
        "SELECT id FROM form WHERE lemma_id = ? AND is_lemma = 1 "
        "ORDER BY id LIMIT 1",
        (m["id"],),
    ).fetchone()
    return {
        "lemma_id": m["id"],
        "lemma": m["word"],
        "pos": m["pos"],
        "gloss": m["gloss"] or "",
        "path": path,
        "family_head": head_row["word"] if head_row else "",
        "entry_id": str(entry_row["id"]) if entry_row else None,
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
        "SELECT id, word, pos, gloss, freq, relation, relation_label, sort_key FROM lemma "
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

    # Ancestry layer: the derivation tree, the ancestor chain, and the
    # cousins share the selected lemma's deepest usable non-proto etymon.
    # The etymon/derivation tables may be absent (pre-ancestry database):
    # the new keys degrade to the documented empty shapes.
    has_etymon = _has_table(conn, "etymon")
    has_derivation = _has_table(conn, "derivation")
    selected_lemma_id = row["lemma_id"]

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
        "tree": _family_tree(conn, head_id, members_sorted, forms_map, selected_lemma_id, has_derivation),
        "ancestry": _ancestry_for(conn, selected_lemma_id, selected_row["lemma"], has_etymon),
        "cousins": _cousins_for(conn, selected_lemma_id, family_id, has_etymon),
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
