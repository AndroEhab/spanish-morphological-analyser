"""Tests for the SQLite backend (app/store_sqlite.py).

Builds a small temporary database with the exact production schema and a
handful of rows covering the mienta ambiguity, a same-word homograph pair,
a clitic form and a multi-POS family. None of this touches the real
300 MB ``data/morph.sqlite`` (the store's DB path is overridden via
``MORPH_SQLITE_PATH``).
"""

import json
import os
import sqlite3
import threading

import pytest

_SCHEMA = [
    """CREATE TABLE lemma (
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
        )""",
    """CREATE TABLE form (
            id INTEGER PRIMARY KEY,
            form TEXT NOT NULL,
            key TEXT NOT NULL,
            lemma_id INTEGER NOT NULL REFERENCES lemma(id),
            features TEXT NOT NULL,
            is_lemma INTEGER NOT NULL DEFAULT 0,
            is_clitic INTEGER NOT NULL DEFAULT 0,
            freq REAL NOT NULL DEFAULT 0
        )""",
    """CREATE TABLE family (
            id INTEGER PRIMARY KEY,
            head_lemma_id INTEGER NOT NULL REFERENCES lemma(id),
            note TEXT,
            size INTEGER NOT NULL DEFAULT 0
        )""",
    "CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)",
    "CREATE INDEX lemma_family_idx ON lemma(family_id)",
    "CREATE INDEX form_key_freq_idx ON form(key, freq)",
    "CREATE INDEX form_lemma_idx ON form(lemma_id)",
    "CREATE INDEX form_key_idx ON form(key)",
]


def _build_db(path) -> None:
    con = sqlite3.connect(str(path))
    for stmt in _SCHEMA:
        con.execute(stmt)

    def lemma(id_, word, pos, freq, family_id, gloss, relation="", relation_label="", etym_no=0):
        con.execute(
            "INSERT INTO lemma (id, word, pos, etym_no, gloss, freq, family_id, relation, relation_label, sort_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (id_, word, pos, etym_no, gloss, freq, family_id, relation, relation_label),
        )

    def form(id_, form, lemma_id, features, freq, is_lemma=0, is_clitic=0):
        con.execute(
            "INSERT INTO form (id, form, key, lemma_id, features, is_lemma, is_clitic, freq) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (id_, form, _fold_key(form), lemma_id, json.dumps(features), is_lemma, is_clitic, freq),
        )

    # family 1: mentir (head) with noun + adj members
    lemma(1, "mentir", "verb", 100.0, 1, "to lie", "root", "root")
    lemma(2, "mentira", "noun", 40.0, 1, "lie, falsehood", "derived", "")   # fallback label
    lemma(3, "mentiroso", "adj", 30.0, 1, "lying", "paradigm", "")          # fallback label
    # family 2: mentar
    lemma(4, "mentar", "verb", 10.0, 2, "to mention", "root", "root")
    # family 3: hacer head + two same-word haz homographs + a second verb
    lemma(5, "haz", "noun", 20.0, 3, "bundle", "affix", "", etym_no=1)
    lemma(6, "haz", "noun", 15.0, 3, "face", "inherited", "inherited from Latin root fac", etym_no=3)
    lemma(7, "hacer", "verb", 200.0, 3, "to do", "root", "root")
    lemma(8, "deshacer", "verb", 100.0, 3, "to undo", "paradigm", "")
    lemma(9, "hacer popó", "verb", 500.0, 3, "to poo", "root", "")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (1, 1, 'test note', 4)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (2, 4, NULL, 1)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (3, 7, NULL, 4)")

    # mentir forms: citation, two presents, the mienta ambiguity (analysis
    # split across two rows, as the pipeline emits), and a clitic form.
    form(101, "mentir", 1, ["infinitive"], 100.0, is_lemma=1)
    form(102, "miento", 1, ["present indicative, 1st singular"], 30.0)
    form(103, "mientes", 1, ["present indicative, 2nd singular"], 20.0)
    form(104, "mienta", 1, ["present subjunctive, 1st singular"], 28.0)
    form(105, "mienta", 1, ["present subjunctive, 3rd singular"], 28.0)
    form(106, "mentirlo", 1, ["infinitive + 3rd person object singular object accusative clitic"], 5.0, is_clitic=1)
    form(107, "mentira", 2, ["singular"], 40.0, is_lemma=1)
    form(108, "mentiras", 2, ["plural"], 20.0)
    form(109, "mentiroso", 3, ["masculine singular"], 30.0, is_lemma=1)
    form(110, "mentirosa", 3, ["feminine singular"], 15.0)
    # mentar: shares the 'mienta' surface form (different lemma_id)
    form(111, "mentar", 4, ["infinitive"], 10.0, is_lemma=1)
    form(112, "mienta", 4, ["present indicative, 3rd singular"], 8.0)
    # hacer family
    form(113, "hacer", 7, ["infinitive"], 200.0, is_lemma=1)
    form(114, "hacerlo", 7, ["infinitive + 3rd person object singular object accusative clitic"], 300.0, is_clitic=1)
    form(115, "haces", 7, ["present indicative, 2nd singular"], 180.0)
    form(116, "hacía", 7, ["imperfect indicative, 1st singular", "imperfect indicative, 3rd singular"], 100.0)
    form(117, "deshacer", 8, ["infinitive"], 100.0, is_lemma=1)
    form(118, "haz", 5, ["singular"], 20.0, is_lemma=1)
    form(119, "haces", 5, ["plural"], 12.0)
    form(120, "haz", 6, ["singular"], 15.0, is_lemma=1)
    form(121, "haces", 6, ["plural"], 10.0)
    form(122, "hacer popó", 9, ["infinitive"], 500.0, is_lemma=1)

    # meta counts deliberately differ from reality (n_forms) to prove that
    # health() reads meta rather than COUNT(*).
    con.execute("INSERT INTO meta (k, v) VALUES ('n_forms', '999')")
    con.execute("INSERT INTO meta (k, v) VALUES ('n_lemmas', '8')")
    con.execute("INSERT INTO meta (k, v) VALUES ('n_families', '3')")
    con.commit()
    con.close()


def _fold_key(text: str) -> str:
    from pipeline.normalize import fold  # same key builder the pipeline uses

    return fold(text)


@pytest.fixture(scope="session")
def store(tmp_path_factory):
    db = tmp_path_factory.mktemp("sqlite_store") / "test.sqlite"
    _build_db(db)
    os.environ["MORPH_SQLITE_PATH"] = str(db)
    import app.store_sqlite
    import importlib

    importlib.reload(app.store_sqlite)  # pick up the env override even if imported earlier
    return app.store_sqlite


def test_search_tier0_exact_beats_higher_freq_prefix(store):
    # 'hacer' (tier 0, freq 200) must rank ahead of 'hacerlo' (tier 1,
    # freq 300) — the exact tier dominates frequency.
    rows = store.search("hacer", 25)
    forms = [r["form"] for r in rows]
    assert forms[0] == "hacer"
    assert "hacerlo" in forms
    assert forms.index("hacer") < forms.index("hacerlo")
    assert rows[0]["is_lemma"] is True


def test_search_tier1_orders_by_freq_desc(store):
    # Groups are ordered by their best frequency: hacerlo(300), hacer(200),
    # haces(180), hacía(100); the three same-form 'haces' rows stay adjacent
    # inside their group, ordered by their own frequency.
    rows = store.search("hac", 25)
    assert [r["form"] for r in rows] == [
        "hacerlo", "hacer", "haces", "haces", "haces", "hacía", "hacer popó",
    ]
    haces = [r for r in rows if r["form"] == "haces"]
    assert [r["freq"] for r in haces] == [180.0, 12.0, 10.0]


def test_search_mienta_group_never_split_and_merged_features(store):
    # limit=1 cannot fit the 2-row mienta group -> dropped whole.
    assert store.search("mienta", 1) == []
    rows = store.search("mienta", 25)
    mienta = [r for r in rows if r["form"] == "mienta"]
    assert len(mienta) == 2
    assert {r["lemma"] for r in mienta} == {"mentir", "mentar"}
    # both rows carry a qualifier (distinct lemma_ids)
    assert all(r["qualifier"] for r in mienta)
    # the mentir row merges the analysis split across two duplicate rows
    mentir_row = next(r for r in mienta if r["lemma"] == "mentir")
    assert set(mentir_row["features"]) == {
        "present subjunctive, 1st singular",
        "present subjunctive, 3rd singular",
    }


def test_search_homograph_qualifier_over_lemma_id(store):
    # 'haz' has two lemmas (bundle / face) with the same word; both rows must
    # get a qualifier (ambiguity is over lemma_id, not lemma word).
    rows = store.search("haces", 25)
    haz = [r for r in rows if r["lemma"] == "haz"]
    assert len(haz) == 2
    assert all(r["qualifier"] == "haz" for r in haz)
    assert {r["gloss"] for r in haz} == {"bundle", "face"}


def test_analyze_group_order_and_labels(store):
    entry_id = store.search("mentir", 5)[0]["id"]
    data = store.analyze(entry_id)
    assert data is not None
    assert data["selected"]["lemma"] == "mentir"
    assert data["family"]["head"] == {"lemma": "mentir", "pos": "verb", "gloss": "to lie"}
    assert data["family"]["note"] == "test note"
    assert [(g["pos"], g["pos_label"]) for g in data["family"]["groups"]] == [
        ("verb", "Verbs"),
        ("noun", "Nouns"),
        ("adj", "Adjectives"),
    ]


def test_analyze_member_and_form_ordering(store):
    entry_id = store.search("mentir", 5)[0]["id"]
    data = store.analyze(entry_id)
    verb_group = data["family"]["groups"][0]
    mentir = next(m for m in verb_group["members"] if m["lemma"] == "mentir")
    assert mentir["is_head"] is True
    assert mentir["relation"] == "root"
    assert mentir["relation_label"] == "root"
    forms = [f["form"] for f in mentir["forms"]]
    # citation first, then grammatical order, clitic last
    assert forms == ["mentir", "miento", "mientes", "mienta", "mentirlo"]
    mienta_view = next(f for f in mentir["forms"] if f["form"] == "mienta")
    assert mienta_view["features"] == (
        "present subjunctive, 1st singular \u00b7 present subjunctive, 3rd singular"
    )
    # fallback relation labels derived from the relation field
    mentira = next(m for m in data["family"]["groups"][1]["members"] if m["lemma"] == "mentira")
    assert mentira["relation_label"] == "related to mentir"
    mentiroso = next(m for m in data["family"]["groups"][2]["members"] if m["lemma"] == "mentiroso")
    assert mentiroso["relation_label"] == "same paradigm as mentir"


def test_analyze_members_head_first_then_freq(store):
    entry_id = store.search("haz", 25)[0]["id"]
    data = store.analyze(entry_id)
    groups = {g["pos"]: g for g in data["family"]["groups"]}
    verb_members = [m["lemma"] for m in groups["verb"]["members"]]
    assert verb_members == ["hacer", "hacer popó", "deshacer"]  # head first, then freq desc
    noun_members = [(m["lemma"], m["gloss"]) for m in groups["noun"]["members"]]
    assert noun_members == [("haz", "bundle"), ("haz", "face")]  # freq desc (20 > 15)
    # non-empty relation_label passthrough
    haz_face = next(m for m in groups["noun"]["members"] if m["gloss"] == "face")
    assert haz_face["relation_label"] == "inherited from Latin root fac"


def test_multi_word_forms_rank_below_single_words(store):
    # 'hacer popó' carries the highest freq (500) but is a multi-word entry;
    # within tier 1 every single-word form must sort before it.
    rows = store.search("hac", 25)
    forms = [r["form"] for r in rows]
    assert "hacer popó" in forms
    idx = forms.index("hacer popó")
    assert all(" " not in f for f in forms[:idx]), forms[: idx + 1]
    assert idx == len(forms) - 1


def test_analyze_404(store):
    assert store.analyze("999999999999") is None
    assert store.analyze("not-an-id") is None
    assert store.analyze("") is None


def test_health_reads_meta(store):
    body = store.health()
    assert body["status"] == "ok"
    assert body["backend"] == "sqlite"
    # n_forms in meta is deliberately '999' while the real count is 21:
    # health must prefer meta over COUNT(*).
    assert body["entries"] == 999
    assert body["lemmas"] == 8
    assert body["families"] == 3


def test_missing_db_fails_cleanly(store, tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DB_PATH", tmp_path / "does-not-exist.sqlite")
    monkeypatch.setattr(store, "_thread", threading.local())
    with pytest.raises(store.StoreError):
        store.search("hacer", 5)


def test_incomplete_schema_fails_cleanly(store, tmp_path, monkeypatch):
    db = tmp_path / "partial.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE lemma (id INTEGER PRIMARY KEY)")  # only one table
    con.commit()
    con.close()
    monkeypatch.setattr(store, "_DB_PATH", db)
    monkeypatch.setattr(store, "_thread", threading.local())
    with pytest.raises(store.StoreError):
        store.health()
