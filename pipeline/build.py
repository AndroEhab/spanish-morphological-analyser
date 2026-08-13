"""Orchestrator: run the full pipeline -> data/morph.sqlite.

Usage: python -m pipeline.build
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from collections import defaultdict
from typing import Any

from pipeline.normalize import build_key, fold
from pipeline.tags import humanize, feature_sort_key
from pipeline.extract import extract as extract_pass1
from pipeline.etymology import parse_templates
from pipeline.paradigm import compute_paradigm_key, get_family_forming_buckets, compute_allomorphs, strip_one_prefix
from pipeline.family import FamilyBuilder, _LATIN_PREFIXES
from pipeline.frequency import load as load_frequency


ROOT = Path(__file__).resolve().parent.parent
JSONL_PATH = ROOT / "kaikki.org-dictionary-Spanish.jsonl"
FREQ_PATH = ROOT / "es_full.txt"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "morph.sqlite"
REJECT_PATH = DATA_DIR / "reject_hacer.txt"

# --------------------------------------------------------------------------
# Etymon table support: language labels and ancestry-row building.
# --------------------------------------------------------------------------

# Language code -> human label for the etymon table / API.
_LANG_LABELS = {
    "la": "Latin", "la-lat": "Late Latin", "la-vul": "Vulgar Latin",
    "la-med": "Medieval Latin", "la-eme": "Early Medieval Latin",
    "la-ecc": "Ecclesiastical Latin", "la-new": "New Latin",
    "osp": "Old Spanish", "es": "Spanish", "fro": "Old French",
    "frm": "Middle French", "fr": "French", "it": "Italian",
    "pt": "Portuguese", "ca": "Catalan", "oc": "Occitan", "ro": "Romanian",
    "ine-pro": "Proto-Indo-European", "itc-pro": "Proto-Italic",
    "gem-pro": "Proto-Germanic", "cel-pro": "Proto-Celtic",
    "grk-pro": "Proto-Greek", "sla-pro": "Proto-Slavic",
    "bat-pro": "Proto-Baltic", "sem-pro": "Proto-Semitic",
    "afa-pro": "Proto-Afroasiatic", "ine": "Indo-European",
    "qfa-sub": "Substratum",
    "ar": "Arabic", "xaa": "Andalusian Arabic", "got": "Gothic",
    "grc": "Ancient Greek", "nah": "Nahuatl", "nci": "Classical Nahuatl",
    "qu": "Quechua", "eu": "Basque", "en": "English", "de": "German",
    "nl": "Dutch", "sa": "Sanskrit", "ja": "Japanese", "he": "Hebrew",
    "frk": "Frankish", "pro": "Old Occitan", "tnq": "Taíno",
    "arn": "Mapudungun", "ota": "Ottoman Turkish", "mis": "Unclassified",
}

# Etymology-tree language NAMES without a mapped code (kept as labels only;
# the tree parser's code map is unchanged so family membership is not).
_LANG_NAME_LABELS = {
    "proto-hellenic": "Proto-Hellenic", "old latin": "Old Latin",
    "proto-west germanic": "Proto-West Germanic", "middle english": "Middle English",
    "old english": "Old English", "classical latin": "Classical Latin",
    "proto-graeco-phrygian": "Proto-Graeco-Phrygian", "frankish": "Frankish",
    "proto-indo-iranian": "Proto-Indo-Iranian", "gaulish": "Gaulish",
    "tagalog": "Tagalog", "old catalan": "Old Catalan",
    "old occitan": "Old Occitan", "classical nahuatl": "Classical Nahuatl",
    "basque": "Basque", "proto-dravidian": "Proto-Dravidian",
    "old high german": "Old High German", "proto-austronesian": "Proto-Austronesian",
    "proto-iranian": "Proto-Iranian", "egyptian": "Egyptian",
    "proto-malayo-polynesian": "Proto-Malayo-Polynesian",
    "old galician-portuguese": "Old Galician-Portuguese",
    "middle dutch": "Middle Dutch", "middle high german": "Middle High German",
    "old dutch": "Old Dutch", "proto-slavic": "Proto-Slavic",
    "anglo-norman": "Anglo-Norman", "taíno": "Taíno", "old norse": "Old Norse",
    "proto-philippine": "Proto-Philippine", "andalusian": "Andalusian",
    "akkadian": "Akkadian", "old french": "Old French",
    "vulgar latin": "Vulgar Latin", "medieval latin": "Medieval Latin",
    "proto-italic": "Proto-Italic", "proto-indo-european": "Proto-Indo-European",
    "proto-germanic": "Proto-Germanic", "proto-greek": "Proto-Greek",
    "old spanish": "Old Spanish", "ancient greek": "Ancient Greek",
}

# Languages excluded from the cousins join (proto reconstructions and
# template-name artifacts); mirrors family._BANNED_LANGS plus the junk codes.
_PROTO_LANGS = frozenset({
    "ine-pro", "itc-pro", "gem-pro", "cel-pro", "grk-pro",
    "sla-pro", "bat-pro", "ine", "qfa-sub", "sem-pro", "afa-pro",
})
_JUNK_LANGS = frozenset({"ety", "yesno", "glossary", "lit", "wp", "unc"})

_TABLE_JUNK_RE = re.compile(r"[()<>,.?;]")


def _lang_is_proto(lang: str) -> bool:
    return lang in _PROTO_LANGS or lang.endswith("-pro")


def _strip_latin_prefix(word: str) -> str:
    """Strip at most one Latin prefix using the same closed prefix list the
    family builder's root keys use.  Display-only (cousins join key): the
    result never influences family membership or root keys."""
    w = word.lower()
    for pfx in _LATIN_PREFIXES:
        if w.startswith(pfx) and len(w) > len(pfx) + 2:
            return w[len(pfx):]
    return w


def _lang_label(lang: str, lang_name: str | None) -> str:
    if lang and lang in _LANG_LABELS:
        return _LANG_LABELS[lang]
    if lang_name:
        return _LANG_NAME_LABELS.get(lang_name.strip().lower(), "")
    return ""


def _table_usable(word: str) -> bool:
    """Filter for etymon-table rows: real words, no morpheme/annotation junk.

    Proto reconstructions are kept (the API drops them); bare morphemes
    ("-tos"), annotation artifacts ("h₂elisder.?"), and markup are not.
    """
    if not word or len(word) < 2:
        return False
    if word.startswith("*") or word.startswith("-") or word.endswith("-"):
        return False
    if " " in word or _TABLE_JUNK_RE.search(word):
        return False
    return True


def _etymon_rows_for(rec: dict, parsed: dict) -> list[dict]:
    """Ordered ancestry rows (depth 0 = immediate ancestor) for one lemma.

    Template etymons first (parse order, most recent ancestor first), then
    etymology-tree entries in reverse (root-to-leaf tree order -> the last
    tree line is the immediate ancestor).  Rows are deduplicated by
    (norm, lang, mode) keeping the first occurrence.
    """
    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    word = rec["word"]
    for norm, lang, mode, raw, note in parsed.get("etymons_raw", []):
        lang = lang or ""
        if not _table_usable(norm) or lang in _JUNK_LANGS:
            continue
        key = (norm, lang, mode or "")
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "norm": norm, "lang": lang, "mode": mode or "",
            "word": raw, "note": note, "label": _lang_label(lang, None),
            "norm_root": _strip_latin_prefix(norm),
        })
    for norm, lang, mode, raw, lang_name in reversed(parsed.get("etymtree_raw", [])):
        lang = lang or ""
        if not _table_usable(norm) or lang in _JUNK_LANGS:
            continue
        # The tree's own "Spanish <word>" line is the lemma itself; the
        # norm is accent-folded so the comparison must fold the lemma too
        # ("Spanish seducción" normalizes to 'seduccion').
        if norm == fold(word) and lang == "es":
            continue
        key = (norm, lang, mode or "")
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "norm": norm, "lang": lang, "mode": mode or "",
            "word": raw, "note": None, "label": _lang_label(lang, lang_name),
            "norm_root": _strip_latin_prefix(norm),
        })
    for i, row in enumerate(rows):
        row["depth"] = i
    return rows


def _is_placeholder_form(surface: str) -> bool:
    """True if a surface form is empty or consists only of dashes/punctuation."""
    s = surface.strip()
    return not s or not any(ch.isalnum() for ch in s)


def _citation_features(pos: str, gender: str) -> list[str]:
    """Humanized features for a lemma's own citation-form row.

    kaikki's forms[] lists only the INFLECTED forms, so the headword itself
    (the entry's word) needs an explicit row to be searchable under its own
    spelling. Verbs take the infinitive; nouns/adjectives take the gender
    from the head template when known; everything else is 'citation form'.
    """
    if pos == "verb":
        return ["infinitive"]
    if pos in ("noun", "adj") and gender in ("masculine", "feminine"):
        return [f"{gender} singular"]
    return ["citation form"]


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def main():
    t0 = time.time()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # ------------------------------------------------------------------
    # Pass 1: extraction
    # ------------------------------------------------------------------
    print(f"[{_ts()}] Pass 1: extracting from JSONL...")
    t1 = time.time()
    
    n_lemmas, n_forms, n_links = extract_pass1(JSONL_PATH, DATA_DIR)
    
    t_extract = time.time() - t1
    print(f"[{_ts()}]   Extracted {n_lemmas} lemmas, {n_links} form links "
          f"({t_extract:.1f}s)")
    
    # ------------------------------------------------------------------
    # Load lemma records
    # ------------------------------------------------------------------
    print(f"[{_ts()}] Loading lemma records...")
    lemma_records: dict[int, dict] = {}
    lemma_forms_raw: dict[int, list[dict]] = {}
    
    with open(DATA_DIR / "lemmas.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            lid = rec["id"]
            lemma_records[lid] = rec
            lemma_forms_raw[lid] = rec.get("forms", [])
    
    # ------------------------------------------------------------------
    # Etymology parsing
    # ------------------------------------------------------------------
    print(f"[{_ts()}] Parsing etymologies...")
    t2 = time.time()
    
    internal_edges: list[dict] = []
    etymon_edges: list[dict] = []
    doublet_edges: list[dict] = []
    etymtree_edges: list[dict] = []
    prose_edges: list[dict] = []
    ancestry_rows: dict[int, list[dict]] = {}

    
    for lid, rec in lemma_records.items():
        word = rec["word"]
        etym_templates = rec.get("etymology_templates", "[]")
        etym_text = rec.get("etymology_text", "")
        
        parsed = parse_templates(word, etym_templates, etym_text)

        rows = _etymon_rows_for(rec, parsed)
        if rows:
            ancestry_rows[lid] = rows
        
        for parent_word, affix in parsed["internal"]:
            internal_edges.append({
                "lemma_id": lid,
                "parent_word": parent_word,
                "affix": affix,
            })
        for ancestor, lang, mode, source_word in parsed["etymons"]:
            etymon_edges.append({
                "lemma_id": lid,
                "ancestor": ancestor,
                "lang": lang,
                "mode": mode,
                "source_word": source_word,
            })
        
        for twin in parsed["doublets"]:
            doublet_edges.append({
                "lemma_id": lid,
                "twin": twin,
            })
        
        for ancestor, lang in parsed["etymtree_ancestors"]:
            etymtree_edges.append({
                "lemma_id": lid,
                "ancestor": ancestor,
                "lang": lang,
            })

        for parent_word, kind in parsed["prose"]:
            prose_edges.append({
                "lemma_id": lid,
                "parent_word": parent_word,
                "kind": kind,
            })

    
    t_etym = time.time() - t2
    print(f"[{_ts()}]   {len(internal_edges)} internal, {len(etymon_edges)} etymon, "
          f"{len(doublet_edges)} doublet, {len(etymtree_edges)} etymtree edges "
          f"({t_etym:.1f}s)")
    # ------------------------------------------------------------------
    # Frequency
    # ------------------------------------------------------------------
    print(f"[{_ts()}] Loading FrequencyWords frequencies...")
    t_freq_start = time.time()
    freq_map = load_frequency(FREQ_PATH)
    t_freq = time.time() - t_freq_start
    print(f"[{_ts()}]   {len(freq_map)} distinct words ({t_freq:.1f}s)")
    
    # Attach frequency to lemma records
    for lid, rec in lemma_records.items():
        w = rec["word"].lower()
        rec["freq"] = freq_map.get(w, 0.0)
    
    # ------------------------------------------------------------------
    # Paradigm analysis
    # ------------------------------------------------------------------
    print(f"[{_ts()}] Computing paradigm keys...")
    t3 = time.time()
    
    from pipeline.paradigm import build_paradigm_buckets
    # Build buckets
    verbs = []
    for lid, rec in lemma_records.items():
        if rec.get("pos") == "verb" and lemma_forms_raw.get(lid):
            verbs.append({"id": lid, "forms": lemma_forms_raw[lid]})
    
    raw_buckets = build_paradigm_buckets(verbs)
    ff_buckets = get_family_forming_buckets(raw_buckets)
    
    t_paradigm = time.time() - t3
    print(f"[{_ts()}]   {len(raw_buckets)} raw buckets, {len(ff_buckets)} family-forming "
          f"({t_paradigm:.1f}s)")
    
    # Bucket size histogram
    sizes = sorted(len(v) for v in raw_buckets.values())
    print(f"[{_ts()}]   Bucket size range: {sizes[0] if sizes else 0}-{sizes[-1] if sizes else 0}")
    print(f"[{_ts()}]   Family-forming buckets (<={40}):")
    ff_sorted = sorted(ff_buckets.values(), key=len, reverse=True)
    for i, bucket in enumerate(ff_sorted[:15]):
        example = None
        for vid in bucket:
            if vid in lemma_records:
                example = lemma_records[vid]["word"]
                break
        print(f"      {len(bucket):4d} verbs  e.g. {example}")
    
    # Store paradigm prefix per verb
    paradigm_prefix: dict[int, str] = {}
    paradigm_key: dict[int, tuple] = {}
    for lid, rec in lemma_records.items():
        if rec.get("pos") == "verb":
            forms = lemma_forms_raw.get(lid, [])
            result = compute_paradigm_key(forms)
            if result:
                P, residual = result
                paradigm_prefix[lid] = P
                paradigm_key[lid] = residual
    
    # ------------------------------------------------------------------
    # Family construction
    # ------------------------------------------------------------------
    print(f"[{_ts()}] Building families...")
    t4 = time.time()
    
    builder = FamilyBuilder()
    builder.load_lemmas(list(lemma_records.values()))
    builder.load_internal_edges(internal_edges)
    builder.load_etymon_edges(etymon_edges)
    builder.load_etymtree_edges(etymtree_edges)
    builder.load_prose_edges(prose_edges)
    builder.load_paradigm_buckets(lemma_forms_raw)
    
    # Load derived and related links (related is substring-gated in E4b).
    derived_links: dict[int, list[str]] = {}
    related_links: dict[int, list[str]] = {}
    for lid, rec in lemma_records.items():
        dr = rec.get("derived", [])
        if dr:
            derived_links[lid] = dr
        rl = rec.get("related", [])
        if rl:
            related_links[lid] = rl
    builder.load_derived_links(derived_links)
    builder.load_related_links(related_links)
    
    families = builder.build(reject_log_path=str(REJECT_PATH))
    
    t_family = time.time() - t4
    print(f"[{_ts()}]   {len(families)} families ({t_family:.1f}s)")
    
    # Hub ancestor report
    hubs = getattr(builder, '_last_hubs', [])
    if hubs:
        print(f"[{_ts()}]   Hub ancestors (fan-out > 400):")
        for anc, sz in hubs[:20]:
            print(f"      {sz:6d}  {anc}")
    
    # ------------------------------------------------------------------
    # Write SQLite
    # ------------------------------------------------------------------
    print(f"[{_ts()}] Writing SQLite database...")
    t5 = time.time()
    _write_sqlite(
        lemma_records, lemma_forms_raw,
        builder, families, freq_map,
        paradigm_prefix, paradigm_key,
        ancestry_rows,
    )
    t_sqlite = time.time() - t5

def _write_sqlite(
    lemma_records: dict[int, dict],
    lemma_forms_raw: dict[int, list[dict]],
    builder: FamilyBuilder,
    families: dict[int, dict],
    freq_map: dict[str, float],
    paradigm_prefix: dict[int, str],
    paradigm_key: dict[int, tuple],
    ancestry_rows: dict[int, list[dict]],
):
    """Write the final SQLite database."""
    
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("BEGIN")
    
    # Schema
    conn.executescript("""
        CREATE TABLE lemma (
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL,
            pos TEXT NOT NULL,
            etym_no INTEGER NOT NULL DEFAULT 0,
            gloss TEXT,
            head_expansion TEXT,
            freq REAL NOT NULL DEFAULT 0,
            family_id INTEGER,
            relation TEXT,
            relation_label TEXT,
            sort_key INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE form (
            id INTEGER PRIMARY KEY,
            form TEXT NOT NULL,
            key TEXT NOT NULL,
            lemma_id INTEGER NOT NULL REFERENCES lemma(id),
            features TEXT NOT NULL,
            is_lemma INTEGER NOT NULL DEFAULT 0,
            is_clitic INTEGER NOT NULL DEFAULT 0,
            freq REAL NOT NULL DEFAULT 0,
            UNIQUE(form, lemma_id)
        );
        CREATE TABLE family (
            id INTEGER PRIMARY KEY,
            head_lemma_id INTEGER NOT NULL REFERENCES lemma(id),
            note TEXT,
            size INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
        CREATE INDEX form_key_idx ON form(key);
        CREATE INDEX form_lemma_idx ON form(lemma_id);
        CREATE INDEX lemma_family_idx ON lemma(family_id);
        CREATE INDEX form_key_freq_idx ON form(key, freq DESC);
        CREATE INDEX form_key_freq_form_idx ON form(key, freq DESC, form);
        CREATE TABLE etymon (
            id INTEGER PRIMARY KEY,
            lemma_id INTEGER NOT NULL REFERENCES lemma(id),
            depth INTEGER NOT NULL,          -- 0 = the immediate ancestor, increasing back in time
            lang TEXT NOT NULL,              -- 'la', 'osp', 'ine-pro', 'ar', ... ('' when unmapped)
            lang_label TEXT NOT NULL,        -- 'Latin', 'Old Spanish', 'Proto-Indo-European', 'Arabic'
            word TEXT NOT NULL,              -- as written in the source, macrons preserved
            norm TEXT NOT NULL,              -- accent/macron-stripped, lowercased — the join key
            norm_root TEXT NOT NULL,         -- norm with at most one Latin prefix stripped — cousins fallback join key
            mode TEXT NOT NULL,              -- inherited | borrowed | derived | root | ''
            note TEXT                        -- e.g. 'ob- + iactāre' when the source states the decomposition
        );
        CREATE INDEX etymon_lemma_idx ON etymon(lemma_id);
        CREATE INDEX etymon_norm_idx ON etymon(norm);
        CREATE INDEX etymon_norm_root_idx ON etymon(norm_root);
        CREATE TABLE derivation (          -- the derivation tree inside a family
            child_id  INTEGER NOT NULL REFERENCES lemma(id),
            parent_id INTEGER NOT NULL REFERENCES lemma(id),
            relation  TEXT NOT NULL,         -- affix | paradigm | prose | root-key | derived | homograph
            label     TEXT NOT NULL,         -- the existing human label, e.g. 'hacer + -dor'
            PRIMARY KEY (child_id)
        );
    """)

    # Build family_id -> members
    family_members: dict[int, list[int]] = defaultdict(list)
    for fid, fam in families.items():
        for mid in fam["members"]:
            family_members[fid].append(mid)

    # Etymon rows: the parsed ancestor chain per lemma, depth 0 = immediate.
    n_etymon = 0
    for lid, rows in ancestry_rows.items():
        for row in rows:
            conn.execute(
                "INSERT INTO etymon (lemma_id, depth, lang, lang_label, word, norm, norm_root, mode, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (lid, row["depth"], row["lang"], row["label"], row["word"],
                 row["norm"], row["norm_root"], row["mode"], row["note"]),
            )
            n_etymon += 1
    print(f"[{_ts()}]   {n_etymon} etymon rows for {len(ancestry_rows)} lemmas")

    # ------------------------------------------------------------------
    # Collect all forms: dedup by (form, lemma_id), merge analyses.
    # Per-form frequency comes from the FrequencyWords word-form list; a
    # form missing from it gets 0.0. Placeholder surfaces (bare dashes
    # or punctuation) are dropped here so they never reach the DB.
    # ------------------------------------------------------------------
    _form_rows: dict[tuple, dict] = {}
    _max_freq = 0.0
    _dropped_placeholders = 0

    for lid, rec in lemma_records.items():
        word = rec["word"]
        for f in rec.get("forms", []):
            f_text = f.get("form", "")
            if _is_placeholder_form(f_text):
                _dropped_placeholders += 1
                continue
            tags = f.get("tags", [])
            key = (f_text, lid)
            sf = freq_map.get(f_text.lower(), 0.0)
            if sf > _max_freq:
                _max_freq = sf
            if key not in _form_rows:
                _form_rows[key] = {"features": set(), "is_lemma": 0, "is_clitic": 0, "freq": sf}
            row = _form_rows[key]
            fs = humanize(tags)
            if fs:
                row["features"].add(fs)
            if "combined-form" in tags:
                row["is_clitic"] = 1
            if f_text == word:
                row["is_lemma"] = 1

    with open(DATA_DIR / "forms.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            fl = json.loads(line)
            f_text = fl["form"]
            if _is_placeholder_form(f_text):
                _dropped_placeholders += 1
                continue
            lid = fl["lemma_id"]
            key = (f_text, lid)
            sf = freq_map.get(f_text.lower(), 0.0)
            if sf > _max_freq:
                _max_freq = sf
            if key not in _form_rows:
                _form_rows[key] = {"features": set(), "is_lemma": 0, "is_clitic": 0, "freq": sf}
            row = _form_rows[key]
            fs = humanize(fl.get("features", []))
            if fs:
                row["features"].add(fs)
            if fl.get("is_clitic"):
                row["is_clitic"] = 1
            if fl.get("is_lemma"):
                row["is_lemma"] = 1

    # H1: every lemma must have a form row for its own citation form
    # (kaikki forms[] lists inflected forms only; the headword is the
    # entry's word and is usually absent from them). Merge when a row
    # already exists: force is_lemma and union the features.
    n_citation_added = 0
    for lid, rec in lemma_records.items():
        word = rec.get("word", "")
        if _is_placeholder_form(word):
            continue
        key = (word, lid)
        sf = freq_map.get(word.lower(), 0.0)
        if key in _form_rows:
            row = _form_rows[key]
            row["is_lemma"] = 1
            row["features"].update(_citation_features(rec.get("pos", ""), rec.get("gender", "")))
        else:
            _form_rows[key] = {
                "features": set(_citation_features(rec.get("pos", ""), rec.get("gender", ""))),
                "is_lemma": 1,
                "is_clitic": 0,
                "freq": sf,
            }
            n_citation_added += 1
            if sf > _max_freq:
                _max_freq = sf

    # lemma.freq = MAX(form.freq) over the lemma's own forms (0.0 if none).
    _lemma_freq: dict[int, float] = {}
    for (_f_text, lid), info in _form_rows.items():
        if info["freq"] > _lemma_freq.get(lid, 0.0):
            _lemma_freq[lid] = info["freq"]

    print(f"[{_ts()}]   {len(_form_rows)} form rows "
          f"({_dropped_placeholders} placeholder rows dropped, "
          f"{n_citation_added} citation rows added)")

    # Insert lemmas
    lemma_sort_key: dict[int, int] = {}
    for fid, mids in family_members.items():
        # Sort: head first, then by relation priority, then by word
        head_id = families[fid]["head_id"]
        
        def _sort_key(mid):
            rel = families[fid]["members"].get(mid, {})
            rel_priority = {
                "root": 0, "affix": 1, "paradigm": 2,
                "prose": 3, "inherited": 4, "derived": 5,
            }.get(rel.get("relation", ""), 6)
            return (mid != head_id, rel_priority, lemma_records.get(mid, {}).get("word", ""))
        
        sorted_members = sorted(mids, key=_sort_key)
        for i, mid in enumerate(sorted_members):
            lemma_sort_key[mid] = i
    
    n_lemmas = 0
    for lid, rec in lemma_records.items():
        fid = builder.family_of.get(lid)
        member_info = {}
        if fid and lid in families.get(fid, {}).get("members", {}):
            member_info = families[fid]["members"][lid]
        
        fam = families.get(fid, {}) if fid else {}
        head_id = fam.get("head_id")
        # If the lemma is the head and has no specific relation, mark as "root"
        rel = member_info.get("relation", "root" if head_id == lid else "")
        rel_label = member_info.get("relation_label", "root" if head_id == lid else "")
        
        freq = _lemma_freq.get(lid, 0.0)
        
        conn.execute(
            "INSERT INTO lemma (id, word, pos, etym_no, gloss, head_expansion, "
            "freq, family_id, relation, relation_label, sort_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                lid, rec["word"], rec["pos"], rec.get("etym_no", 0),
                rec.get("gloss"), rec.get("head_expansion", ""),
                freq, fid, rel, rel_label,
                lemma_sort_key.get(lid, 0),
            ),
        )
        n_lemmas += 1
    
    # Insert families
    n_families = 0
    for fid, fam in families.items():
        head_id = fam["head_id"]
        size = len(fam["members"])
        conn.execute(
            "INSERT INTO family (id, head_lemma_id, size) VALUES (?, ?, ?)",
            (fid, head_id, size),
        )
        n_families += 1

    # Derivation rows: the BFS parent pointer for every non-head member.
    n_derivation = 0
    n_orphaned_members = 0
    for fid, fam in families.items():
        head_id = fam["head_id"]
        for mid, info in fam["members"].items():
            if mid == head_id:
                continue
            parent_id = info.get("_parent_id")
            if parent_id is None:
                # No derivational parent (root-key/homograph sibling): the
                # tree view attaches it to the head with its own relation.
                n_orphaned_members += 1
                continue
            conn.execute(
                "INSERT INTO derivation (child_id, parent_id, relation, label) "
                "VALUES (?, ?, ?, ?)",
                (mid, parent_id, info.get("relation", ""),
                 info.get("relation_label", "")),
            )
            n_derivation += 1
    print(f"[{_ts()}]   {n_derivation} derivation rows "
          f"({n_orphaned_members} members without a derivational parent)")

    n_forms = 0
    for (f_text, lid), info in sorted(_form_rows.items()):
        features_json = json.dumps(
            sorted(info["features"], key=feature_sort_key), ensure_ascii=False
        )
        conn.execute(
            "INSERT INTO form (form, key, lemma_id, features, is_lemma, is_clitic, freq) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f_text, build_key(f_text), lid, features_json,
             info["is_lemma"], info["is_clitic"], info["freq"]),
        )
        n_forms += 1

    conn.execute(
        "INSERT INTO meta (k, v) VALUES (?, ?)",
        ("n_families", str(n_families)),
    )
    conn.execute(
        "INSERT INTO meta (k, v) VALUES (?, ?)",
        ("max_freq", str(_max_freq)),
    )

    # Finalize
    conn.execute("COMMIT")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("ANALYZE")
    conn.execute("PRAGMA optimize")
    conn.close()


if __name__ == "__main__":
    main()
