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
    """CREATE TABLE etymon (
            id INTEGER PRIMARY KEY,
            lemma_id INTEGER NOT NULL REFERENCES lemma(id),
            depth INTEGER NOT NULL,
            lang TEXT NOT NULL,
            lang_label TEXT NOT NULL,
            word TEXT NOT NULL,
            norm TEXT NOT NULL,
            norm_root TEXT NOT NULL,
            mode TEXT NOT NULL,
            note TEXT
        )""",
    """CREATE TABLE derivation (
            child_id INTEGER NOT NULL REFERENCES lemma(id),
            parent_id INTEGER NOT NULL REFERENCES lemma(id),
            relation TEXT NOT NULL,
            label TEXT NOT NULL,
            PRIMARY KEY (child_id)
        )""",
    "CREATE INDEX lemma_family_idx ON lemma(family_id)",
    "CREATE INDEX form_key_freq_idx ON form(key, freq)",
    "CREATE INDEX form_lemma_idx ON form(lemma_id)",
    "CREATE INDEX form_key_idx ON form(key)",
    "CREATE INDEX etymon_lemma_idx ON etymon(lemma_id)",
    "CREATE INDEX etymon_norm_idx ON etymon(norm)",
    "CREATE INDEX etymon_norm_root_idx ON etymon(norm_root)",
    """CREATE TABLE english_cognate (
        id INTEGER PRIMARY KEY,
        word TEXT NOT NULL,
        pos TEXT NOT NULL,
        gloss TEXT,
        norm TEXT NOT NULL,
        norm_root TEXT NOT NULL
    )""",
    "CREATE INDEX english_cognate_norm_idx ON english_cognate(norm)",
    "CREATE INDEX english_cognate_norm_root_idx ON english_cognate(norm_root)",
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

    # Ancestry layer fixtures.  Family 8 reproduces the real-world objetar
    # story: objetar and desechar sit in echar's family, and the prefixed
    # reflexes all strip to the root iectāre.
    lemma(10, "proyectar", "verb", 50.0, 4, "to project")
    lemma(11, "inyectar", "verb", 20.0, 5, "to inject")
    lemma(12, "sujetar", "verb", 25.0, 6, "to hold")
    lemma(13, "objetar", "verb", 30.0, 8, "to object")
    lemma(14, "echar", "verb", 100.0, 8, "to throw", "root", "root")
    lemma(15, "desechar", "verb", 40.0, 8, "to discard")
    lemma(16, "jactar", "verb", 5.0, 9, "to shake")
    lemma(17, "mental", "adj", 8.0, 10, "mental")
    lemma(18, "mentar", "adj", 2.0, 11, "mental (variant)")
    lemma(19, "mente", "noun", 90.0, 12, "mind")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (4, 10, NULL, 1)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (5, 11, NULL, 1)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (6, 12, NULL, 1)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (8, 14, NULL, 3)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (9, 16, NULL, 1)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (10, 17, NULL, 1)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (11, 18, NULL, 1)")
    con.execute("INSERT INTO family (id, head_lemma_id, note, size) VALUES (12, 19, NULL, 1)")

    # etymon rows: (lemma_id, depth, lang, lang_label, word, norm, norm_root, mode)
    con.executemany(
        "INSERT INTO etymon (lemma_id, depth, lang, lang_label, word, norm, norm_root, mode, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        [
            # mentir: exact shared etymon 'mensa' with mentira/mentiroso
            (1, 0, "la", "Latin", "mensa", "mensa", "mensa", "derived"),
            (2, 0, "la", "Latin", "mensa", "mensa", "mensa", "derived"),
            (3, 0, "la", "Latin", "mensa", "mensa", "mensa", "derived"),
            # echar: full chain ending at iactāre, plus a proto row to test
            # the at-most-one-proto rule
            (14, 0, "la", "Latin", "iecto", "iecto", "iecto", "inherited"),
            (14, 1, "la", "Latin", "iectāre", "iectare", "iectare", "inherited"),
            (14, 2, "la", "Latin", "iacto", "iacto", "iacto", "inherited"),
            (14, 3, "la", "Latin", "iactāre", "iactare", "iactare", "inherited"),
            (14, 4, "ine-pro", "Proto-Indo-European", "h1yag", "h1yag", "h1yag", "derived"),
            (14, 5, "ine-pro", "Proto-Indo-European", "h1yagto", "h1yagto", "h1yagto", "derived"),
            # the prefixed reflexes: all strip to iectare
            (13, 0, "la", "Latin", "obiectāre", "obiectare", "iectare", "borrowed"),
            (15, 0, "la", "Latin", "disiectāre", "disiectare", "iectare", "inherited"),
            (10, 0, "la", "Latin", "prōiectāre", "proiectare", "iectare", "borrowed"),
            (11, 0, "la", "Latin", "iniectāre", "iniectare", "iectare", "borrowed"),
            (12, 0, "la", "Latin", "subiectāre", "subiectare", "iectare", "borrowed"),
            # jactar shares iactāre exactly with echar
            (16, 0, "la", "Latin", "iactāre", "iactare", "iactare", "borrowed"),
            # hacer and deshacer both cite facere: the only exact sharer is
            # deshacer's own family head — no cousins may result
            (7, 0, "la", "Latin", "facere", "facere", "facere", "inherited"),
            (8, 0, "la", "Latin", "facere", "facere", "facere", "inherited"),
            # the mens cluster for the fan-out cap test
            (17, 0, "la", "Latin", "mens", "mens", "mens", "derived"),
            (18, 0, "la", "Latin", "mens", "mens", "mens", "derived"),
            (19, 0, "la", "Latin", "mens", "mens", "mens", "derived"),
        ],
    )

    # derivation rows: the BFS parent pointer per non-head member.
    con.executemany(
        "INSERT INTO derivation (child_id, parent_id, relation, label) VALUES (?, ?, ?, ?)",
        [
            (2, 1, "derived", "related to mentir"),
            (3, 1, "paradigm", "same paradigm as mentir"),
            (8, 7, "paradigm", "same paradigm as hacer"),
            (5, 7, "affix", "haz + -ar"),
            (6, 7, "inherited", "inherited from Latin root fac"),
            # family 8: objetar and desechar attach to echar
            (13, 14, "derived", "related to echar"),
            (15, 14, "affix", "des- + echar"),
        ],
    )

    for lid, word in [(10, "proyectar"), (11, "inyectar"), (12, "sujetar"),
                      (13, "objetar"), (14, "echar"), (15, "desechar"),
                      (16, "jactar"), (17, "mental"), (18, "mentar"), (19, "mente")]:
        con.execute(
            "INSERT INTO form (id, form, key, lemma_id, features, is_lemma, is_clitic, freq) "
            "VALUES (?, ?, ?, ?, '[\"citation form\"]', 1, 0, ?)",
            (200 + lid, word, _fold_key(word), lid, con.execute("SELECT freq FROM lemma WHERE id=?", (lid,)).fetchone()[0]),
        )

    # english_cognate rows (Phase 3, englishRelatives card): one row per
    # (English word, cited Latin norm); the gloss belongs to the entry that
    # cited that norm.
    con.executemany(
        "INSERT INTO english_cognate (word, pos, gloss, norm, norm_root) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("jettison", "verb", "to eject", "iacto", "iacto"),
            ("jetty", "noun", "a pier", "iacto", "iacto"),
            ("parge", "verb", "to apply parge", "iactare", "iactare"),
            ("parget", "noun", "gypsum", "iacto", "iacto"),
            ("adjection", "noun", "act of adding", "adiecto", "iecto"),
            ("subject", "noun", "a topic", "subiecto", "iecto"),
            ("fact", "noun", "a deed", "facere", "facere"),
            ("mental", "adj", "of the mind", "mens", "mens"),
        ],
    )

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


# ---------------------------------------------------------------------------
# Ancestry layer: tree, ancestry chain, cousins (etymon/derivation tables)
# ---------------------------------------------------------------------------

def _analyze_for(store, word: str, pos: str | None = None):
    rows = store.search(word, 25)
    row = next(r for r in rows if r["lemma"] == word and (pos is None or r["pos"] == pos))
    return store.analyze(row["id"]), row


def _analyze_form(store, form: str, lemma: str):
    """Analyze one surface form under a given lemma (inflected forms)."""
    rows = store.search(form, 25)
    row = next(r for r in rows if r["form"] == form and r["lemma"] == lemma)
    return store.analyze(row["id"]), row


def test_analyze_tree_dfs_parent_before_child(store):
    data, _ = _analyze_for(store, "mentir")
    nodes = data["tree"]["nodes"]
    assert data["tree"]["root_lemma_id"] == 1
    assert [(n["lemma"], n["depth"], n["parent_id"], n["relation"], n["label"]) for n in nodes] == [
        ("mentir", 0, None, "root", "root"),
        ("mentira", 1, 1, "derived", "related to mentir"),
        ("mentiroso", 1, 1, "paradigm", "same paradigm as mentir"),
    ]
    assert nodes[0]["pos"] == "verb"
    assert nodes[0]["is_selected"] is True
    assert nodes[1]["form_count"] == 2  # mentira + mentiras
    assert nodes[1]["freq"] == 40.0
    # a non-head selection marks its own node
    data2, _ = _analyze_for(store, "mentira")
    sel = next(n for n in data2["tree"]["nodes"] if n["lemma_id"] == 2)
    assert sel["is_selected"] is True
    assert data2["tree"]["nodes"][0]["is_selected"] is False


def test_analyze_tree_member_without_derivation_row_attaches_to_head(store):
    # family 3 (hacer) has no derivation rows for haz/hacer popó: they attach
    # to the head at depth 1 with their own relation — never orphaned.
    data, _ = _analyze_for(store, "hacer")
    nodes = {n["lemma"]: n for n in data["tree"]["nodes"]}
    assert nodes["hacer"]["depth"] == 0 and nodes["hacer"]["parent_id"] is None
    for w in ("haz", "deshacer", "hacer popó"):
        assert nodes[w]["depth"] == 1, w
        assert nodes[w]["parent_id"] == 7, w
    order = [n["lemma"] for n in data["tree"]["nodes"]]
    assert order.index("hacer") < order.index("hacer popó")
    ids = [n["lemma_id"] for n in data["tree"]["nodes"]]
    assert len(ids) == len(set(ids))  # every member exactly once (haz appears twice: two lemmas)


def test_analyze_ancestry_chain_and_proto_dedup(store):
    data, _ = _analyze_for(store, "echar")
    anc = data["ancestry"]
    assert [a["word"] for a in anc] == [
        "echar", "iecto", "iectāre", "iacto", "iactāre", "h1yag",
    ]
    assert anc[0] == {
        "lang": "es", "lang_label": "Spanish", "word": "echar",
        "mode": None, "note": None, "proto": False,
    }
    assert anc[1]["lang"] == "la" and anc[1]["mode"] == "inherited"
    assert anc[4] == {"lang": "la", "lang_label": "Latin", "word": "iactāre",
                      "mode": "inherited", "note": None, "proto": False}
    # at most one proto link, and it is marked
    protos = [a for a in anc if a["proto"]]
    assert [p["word"] for p in protos] == ["h1yag"]
    assert protos[0]["lang_label"] == "Proto-Indo-European"
    assert len(anc) <= 8


def test_analyze_cousins_exact_norm_join(store):
    # echar cites iactāre itself; jactar cites it too — the exact shared
    # etymon is the strongest signal and wins over the root join.
    data, _ = _analyze_for(store, "echar")
    c = data["cousins"]
    assert c is not None
    assert c["shared_etymon"] == {"lang_label": "Latin", "word": "iactāre", "norm": "iactare"}
    assert [m["lemma"] for m in c["members"]] == ["jactar"]
    m = c["members"][0]
    assert m["path"] == "iactāre"
    assert m["family_head"] == "jactar"
    assert m["pos"] == "verb"
    assert m["entry_id"] is not None


def test_analyze_cousins_norm_root_fallback_excludes_family(store):
    # objetar cites only obiectāre (fan-out 1): the exact join yields
    # nothing, so the cousins come from the prefix-stripped root iectāre.
    # Family members are never cousins: echar (objetar's family head) and
    # desechar are excluded even though they share the root.
    data, _ = _analyze_for(store, "objetar")
    c = data["cousins"]
    assert c is not None
    assert c["shared_etymon"] == {"lang_label": "Latin", "word": "iectāre", "norm": "iectare"}
    lemmas = {m["lemma"]: m for m in c["members"]}
    assert set(lemmas) == {"proyectar", "inyectar", "sujetar"}
    assert lemmas["proyectar"]["path"] == "prōiectāre < pro- + iectāre"
    assert lemmas["inyectar"]["path"] == "iniectāre < in- + iectāre"
    assert lemmas["sujetar"]["path"] == "subiectāre < sub- + iectāre"
    # ranked by frequency desc (proyectar 50 > sujetar 25 > inyectar 20)
    assert [m["lemma"] for m in c["members"]] == ["proyectar", "sujetar", "inyectar"]


def test_analyze_cousins_family_head_excluded_from_exact_join(store):
    # deshacer and hacer both cite facere exactly; the only exact sharer is
    # deshacer's own family head, so the exact join empties after the
    # family exclusion and no cousins block is offered.
    data, _ = _analyze_for(store, "deshacer")
    assert data["cousins"] is None


def test_analyze_cousins_fanout_cap(store, monkeypatch):
    data, _ = _analyze_for(store, "mental")
    c = data["cousins"]
    assert c["shared_etymon"]["norm"] == "mens"
    assert {m["lemma"] for m in c["members"]} == {"mentar", "mente"}
    # tighten the cap: mens has 3 descendants, so it becomes too generic and
    # nothing qualifies -> cousins null
    monkeypatch.setattr(store, "_COUSIN_FANOUT_CAP", 2)
    data2, _ = _analyze_for(store, "mental")
    assert data2["cousins"] is None


def test_analyze_no_etymon_rows_empty_shapes(store):
    # mentar (family 2) has no etymon rows: empty ancestry, null cousins.
    data, _ = _analyze_for(store, "mentar", "verb")
    assert data["ancestry"] == []
    assert data["cousins"] is None
    # the tree still renders (head-only family)
    assert data["tree"]["root_lemma_id"] == 4
    assert data["tree"]["nodes"][0]["lemma"] == "mentar"


def test_analyze_english_relatives_norm_and_root_channels(store):
    # echar cites iacto/iactare exactly (norm channel) and iecto via the
    # stripped roots (norm_root channel): the card shows both channels,
    # direct cognates first, each with the gloss of the row that matched.
    data, _ = _analyze_for(store, "echar")
    rel = data["englishRelatives"]
    assert rel is not None
    assert rel["sharedRoot"] == "iactare"
    assert [it["word"] for it in rel["items"]] == [
        "jettison", "jetty", "parge", "parget", "adjection", "subject",
    ]
    assert [it["relationType"] for it in rel["items"]] == [
        "direct-cognate", "direct-cognate", "direct-cognate", "direct-cognate",
        "shared-latin-root", "shared-latin-root",
    ]
    for it in rel["items"]:
        assert set(it) == {"word", "gloss", "sharedRoot",
                           "relationType", "explanation", "audio"}
        assert it["audio"] is None and it["gloss"] and it["sharedRoot"]
        assert it["explanation"]
    # the norm_root items anchor on the stripped root, not the citation
    assert rel["items"][4]["sharedRoot"] == "iecto"


def test_analyze_english_relatives_exact_norm_only(store):
    # hacer cites facere exactly: only the norm channel fires; the English
    # row's gloss survives the round trip.
    data, _ = _analyze_for(store, "hacer")
    rel = data["englishRelatives"]
    assert rel is not None
    assert [it["word"] for it in rel["items"]] == ["fact"]
    assert rel["items"][0]["relationType"] == "direct-cognate"
    assert rel["items"][0]["gloss"] == "a deed"


def test_analyze_english_relatives_fanout_cap(store, monkeypatch):
    # mens has 3 Spanish descendants; tighten the cap and the card empties
    # exactly like the cousins cap behaves.
    data, _ = _analyze_for(store, "mental")
    assert data["englishRelatives"] is not None
    assert [it["word"] for it in data["englishRelatives"]["items"]] == ["mental"]
    monkeypatch.setattr(store, "_COUSIN_FANOUT_CAP", 2)
    data2, _ = _analyze_for(store, "mental")
    assert data2["englishRelatives"] is None


def test_analyze_without_ancestry_tables_degrades(store, tmp_path, monkeypatch):
    # a pre-ancestry database (no etymon/derivation tables) keeps working:
    # the new keys degrade to the documented empty shapes.
    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE lemma (id INTEGER PRIMARY KEY, word TEXT NOT NULL, pos TEXT NOT NULL, "
        "etym_no INTEGER NOT NULL DEFAULT 0, gloss TEXT, head_expansion TEXT, "
        "freq REAL NOT NULL DEFAULT 0, family_id INTEGER, relation TEXT, "
        "relation_label TEXT, sort_key INTEGER NOT NULL DEFAULT 0)"
    )
    con.execute(
        "CREATE TABLE form (id INTEGER PRIMARY KEY, form TEXT NOT NULL, key TEXT NOT NULL, "
        "lemma_id INTEGER NOT NULL REFERENCES lemma(id), features TEXT NOT NULL, "
        "is_lemma INTEGER NOT NULL DEFAULT 0, is_clitic INTEGER NOT NULL DEFAULT 0, "
        "freq REAL NOT NULL DEFAULT 0)"
    )
    con.execute(
        "CREATE TABLE family (id INTEGER PRIMARY KEY, head_lemma_id INTEGER NOT NULL "
        "REFERENCES lemma(id), note TEXT, size INTEGER NOT NULL DEFAULT 0)"
    )
    con.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
    con.execute(
        "INSERT INTO lemma (id, word, pos, gloss, freq, family_id, relation, relation_label, sort_key) "
        "VALUES (1, 'hacer', 'verb', 'to do', 10.0, 1, 'root', 'root', 0)"
    )
    con.execute("INSERT INTO family (id, head_lemma_id, size) VALUES (1, 1, 1)")
    con.execute(
        "INSERT INTO form (id, form, key, lemma_id, features, is_lemma, freq) "
        "VALUES (1, 'hacer', 'hacer', 1, '[\"infinitive\"]', 1, 10.0)"
    )
    con.commit()
    con.close()
    monkeypatch.setattr(store, "_DB_PATH", db)
    monkeypatch.setattr(store, "_thread", threading.local())
    data = store.analyze("1")
    assert data is not None
    assert data["ancestry"] == []
    assert data["cousins"] is None
    assert data["tree"]["nodes"][0]["lemma"] == "hacer"


# ---------------------------------------------------------------------------
# Phase 1 dashboard keys (frozen §D contract): query, morphology,
# familyPreview, origin, nearbyForms, alternatives.
# ---------------------------------------------------------------------------

def test_analyze_morphology_split_and_summary(store):
    data, _ = _analyze_for(store, "mentir")
    assert data["query"] == "mentir"
    m = data["morphology"]
    assert m["summary"] == "verbo · no personal · infinitivo"
    assert m["lexeme"] == "ment-"
    assert m["inflection"] == "-ir"
    assert m["base"] == "mentir"
    assert m["categoría"] == "verbo"
    assert m["conjugationClass"] == "Tercera (-ir)"
    assert m["conjugación"] == "Tercera (-ir)"
    assert m["decomposition"][0] == {"segment": "ment", "label": "raíz o base léxica", "kind": "stem"}
    assert m["alternatives"] == []


def test_analyze_morphology_accented_desinence_and_no_participle_overstrip(store):
    # "miento" must split mient- + -o, NOT mien- + -to (the participle
    # desinence is excluded by the present-indicative analysis); "hacía"
    # must split hac- + -ía, NOT hací- + -a (the accented desinence matches)
    data, _ = _analyze_form(store, "miento", "mentir")
    m = data["morphology"]
    assert m["lexeme"] == "mient-"
    assert m["inflection"] == "-o"
    assert m["summary"] == "verbo · modo indicativo · presente · 1ª persona del singular"
    data2, _ = _analyze_form(store, "hacía", "hacer")
    assert data2["morphology"]["lexeme"] == "hac-"
    assert data2["morphology"]["inflection"] == "-ía"


def test_analyze_morphology_clitic_form_splits_on_verified_base(store):
    # clitics are stripped against the lemma's own form table first; the
    # inflection shown is the base's (mentir + lo → ment- + -ir)
    data, _ = _analyze_form(store, "mentirlo", "mentir")
    assert data["morphology"]["lexeme"] == "ment-"
    assert data["morphology"]["inflection"] == "-ir"
    data2, _ = _analyze_form(store, "hacerlo", "hacer")
    assert data2["morphology"]["lexeme"] == "hac-"
    assert data2["morphology"]["inflection"] == "-er"


def test_analyze_morphology_multiword_junk_is_null(store):
    # F12: multi-word surfaces never reach the split; the empty state is a
    # null lexeme and an empty decomposition
    data, _ = _analyze_form(store, "hacer popó", "hacer popó")
    m = data["morphology"]
    assert m["lexeme"] is None and m["inflection"] is None
    assert m["decomposition"] == []


def test_analyze_morphology_noun_never_splits(store):
    data, _ = _analyze_for(store, "mentira")
    m = data["morphology"]
    assert m["summary"] == "sustantivo · singular"
    assert m["lexeme"] is None and m["inflection"] is None
    assert m["conjugationClass"] is None
    assert data["nearbyForms"] == []


def test_analyze_alternatives_ranked(store):
    data, _ = _analyze_form(store, "mienta", "mentir")
    alts = data["morphology"]["alternatives"]
    assert [a["lemma"] for a in alts] == ["mentar"]
    alt = alts[0]
    assert alt["pos"] == "verb"
    assert alt["summary"] == "verbo · modo indicativo · presente · 3ª persona del singular"
    assert store.analyze(alt["entry_id"]) is not None  # the chip navigates


def test_analyze_family_preview_ranked_and_selected(store):
    data, _ = _analyze_for(store, "mentir")
    preview = data["familyPreview"]
    assert preview["hub"] == "mentir"
    assert preview["totalCount"] == 4  # the fixture family's real size
    nodes = preview["nodes"]
    assert nodes[0]["lemma"] == "mentir" and nodes[0]["relationLabel"] == "root"
    assert nodes[0]["isSelected"] is True  # searched the head's citation
    # relation-type priority: paradigm (mentiroso) before derived (mentira)
    assert [n["lemma"] for n in nodes[1:]] == ["mentiroso", "mentira"]
    assert sum(1 for n in nodes if n["isSelected"]) == 1
    # searching an inflected form of the head adds a highlighted peripheral node
    data2, _ = _analyze_form(store, "mienta", "mentir")
    sel = [n for n in data2["familyPreview"]["nodes"] if n["isSelected"]]
    assert len(sel) == 1 and sel[0]["lemma"] == "mienta"
    # searching a non-head member marks that member in place
    data3, _ = _analyze_for(store, "mentira")
    sel3 = [n for n in data3["familyPreview"]["nodes"] if n["isSelected"]]
    assert len(sel3) == 1 and sel3[0]["lemma"] == "mentira"


def test_analyze_origin_stages_and_source(store):
    data, _ = _analyze_for(store, "echar")
    origin = data["origin"]
    assert origin is not None
    assert origin["sourceLanguage"] == "latín"
    assert origin["sourceWord"] == "iactāre"  # deepest non-proto step
    assert origin["sourceMeaning"] is None  # Phase 1: no Latin gloss source (docs F7)
    # stages are newest-first per the frozen §D contract ("oldest last"):
    # the Spanish word first, etymons backwards in time
    words = [(s["word"], s["langLabel"]) for s in origin["stages"]]
    assert words == [
        ("echar", "español"),
        ("iecto", "latín"),
        ("iectāre", "latín"),
        ("iacto", "latín"),
        ("iactāre", "latín"),
        ("h1yag", "protoindoeuropeo"),
    ]
    # the ancestry payload itself is unchanged (existing consumers)
    assert data["ancestry"][0]["word"] == "echar"


def test_analyze_origin_null_without_etymon(store):
    data, _ = _analyze_for(store, "mentar", "verb")
    assert data["origin"] is None
    assert data["ancestry"] == []


def test_analyze_nearby_forms_tense_row_and_cap(store):
    # same-tense row: miento (present 1sg) → the present-indicative row;
    # mienta is subjunctive and mentirlo is clitic, so neither qualifies
    data, _ = _analyze_form(store, "miento", "mentir")
    assert [(f["form"], f["features"]) for f in data["nearbyForms"]] == [
        ("miento", "present indicative, 1st singular"),
        ("mientes", "present indicative, 2nd singular"),
    ]
    assert all(f["isLemma"] is False for f in data["nearbyForms"])
    # non-finite searches fall back to the present-indicative row
    data2, _ = _analyze_for(store, "mentir")
    assert [f["form"] for f in data2["nearbyForms"]] == ["miento", "mientes"]
    # no verb → empty strip
    data3, _ = _analyze_for(store, "mentira")
    assert data3["nearbyForms"] == []


def test_analyze_phase2_phase4_keys_null(store):
    data, _ = _analyze_for(store, "mentir")
    assert data["englishRelatives"] is None
    assert data["mnemonics"] is None
    assert data["selected"]["audio"] is None
    assert data["selected"]["ipa"] is None


def test_analyze_summary_gender_number_spanish(store):
    # nouns/adjectives render gender and number in Spanish (the raw feature
    # tokens "masculine"/"singular" must never surface in the Spanish UI)
    data, _ = _analyze_for(store, "mentiroso")
    assert data["morphology"]["summary"] == "adjetivo · masculino singular"
    data2, _ = _analyze_form(store, "mentirosa", "mentiroso")
    assert data2["morphology"]["summary"] == "adjetivo · femenino singular"
    data3, _ = _analyze_form(store, "mentiras", "mentira")
    assert data3["morphology"]["summary"] == "sustantivo · plural"
