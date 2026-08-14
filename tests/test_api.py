"""API contract tests for the Spanish Morphological Analyser."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_mient_returns_two_ambiguous_rows():
    res = client.get("/api/search", params={"q": "mient"})
    assert res.status_code == 200
    data = res.json()
    mienta_rows = [row for row in data["results"] if row["form"] == "mienta"]
    assert len(mienta_rows) == 2
    assert all(row["qualifier"] for row in mienta_rows)
    assert {row["qualifier"] for row in mienta_rows} == {"mentir", "mentar"}


def test_search_hiz_returns_hizo():
    res = client.get("/api/search", params={"q": "hiz"})
    assert res.status_code == 200
    forms = {row["form"] for row in res.json()["results"]}
    assert "hizo" in forms


def test_search_hecho_self_qualifying_rows_carry_their_own_lemma():
    # The parenthesised qualifier exists to name a DIFFERENT lemma: the
    # frontend renders the qualifier cell empty when qualifier == form
    # ("hecho (hecho)" is noise) and only shows it when it disambiguates
    # ("hecho (hacer)").
    res = client.get("/api/search", params={"q": "hecho"})
    assert res.status_code == 200
    rows = [row for row in res.json()["results"] if row["form"] == "hecho"]
    assert len(rows) >= 3
    by_lemma = {row["lemma"]: row for row in rows}
    assert "hacer" in by_lemma
    assert by_lemma["hacer"]["qualifier"] == "hacer"  # rendered as "(hacer)"
    self_rows = [r for r in rows if r["qualifier"] == "hecho"]
    assert self_rows, "expected self-qualifying hecho rows"
    assert all(r["qualifier"] == r["form"] for r in self_rows)  # rendered empty


def test_search_is_accent_insensitive():
    # "hacia" (no accent) must match "hacía" (with accent) in the fixture.
    res = client.get("/api/search", params={"q": "hacia"})
    assert res.status_code == 200
    forms = {row["form"] for row in res.json()["results"]}
    assert "hacía" in forms


def test_analyze_bad_id_returns_404():
    res = client.get("/api/analyze", params={"id": "zzz::noexiste::noun"})
    assert res.status_code == 404


def test_analyze_hacer_group_order_and_members():
    rows = client.get("/api/search", params={"q": "hacer"}).json()["results"]
    hacer_row = next(r for r in rows if r["form"] == "hacer" and r["lemma"] == "hacer")
    res = client.get("/api/analyze", params={"id": hacer_row["id"]})
    assert res.status_code == 200
    data = res.json()
    groups = data["family"]["groups"]
    assert groups and groups[0]["pos"] == "verb"
    verb_lemmas = {m["lemma"] for m in groups[0]["members"]}
    assert "satisfacer" in verb_lemmas


def test_analyze_mienta_mentar_resolves_into_mentar_family():
    # Same surface form under two lemmas must land in the right family.
    # The id is taken from the search rows so the test works against any
    # backend (fixture ids vs. SQLite integer ids are opaque to the client).
    rows = client.get("/api/search", params={"q": "mienta"}).json()["results"]
    mentar_row = next(r for r in rows if r["form"] == "mienta" and r["lemma"] == "mentar")
    res = client.get("/api/analyze", params={"id": mentar_row["id"]})
    assert res.status_code == 200
    data = res.json()
    # the mentar row must resolve to the mentar entry (not mentir); the family
    # head is whatever the pipeline's clustering decided (e.g. cimentar)
    assert data["selected"]["lemma"] == "mentar"
    all_members = {m["lemma"] for g in data["family"]["groups"] for m in g["members"]}
    assert "mentar" in all_members


def test_health_returns_ok():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["entries"] > 0
    assert body["lemmas"] > 0
    assert body["families"] > 0
    assert body["backend"] in ("fixture", "sqlite")


def test_search_hacer_ranks_exact_infinitive_first():
    # Exact form match (tier 0) beats prefix matches (tier 1): "hacer" the
    # infinitive must rank ahead of "hacerlo" even though both match.
    res = client.get("/api/search", params={"q": "hacer"})
    assert res.status_code == 200
    results = res.json()["results"]
    assert results[0]["form"] == "hacer"
    assert results[0]["lemma"] == "hacer"
    assert results[0]["is_lemma"] is True
    forms = [row["form"] for row in results]
    assert "hacerlo" in forms
    assert forms.index("hacer") < forms.index("hacerlo")


def test_search_mienta_group_is_never_split_by_limit():
    # The two mienta rows (mentir / mentar) are alternatives the user picks
    # between: the limit must include or drop the whole group, never split
    # it across the boundary, and the rows must be adjacent.
    for limit in range(1, 14):
        res = client.get("/api/search", params={"q": "mient", "limit": limit})
        assert res.status_code == 200
        mienta = [row for row in res.json()["results"] if row["form"] == "mienta"]
        assert len(mienta) in (0, 2), f"limit={limit}: mienta group split across the cut"
    res = client.get("/api/search", params={"q": "mient", "limit": 25})
    rows = res.json()["results"]
    idxs = [i for i, row in enumerate(rows) if row["form"] == "mienta"]
    assert len(idxs) == 2 and idxs[1] == idxs[0] + 1


# ---------------------------------------------------------------------------
# The three new analyze keys: tree, ancestry, cousins (frozen contract).
# ---------------------------------------------------------------------------

def _analyze_first(query, form=None, lemma=None, pos=None):
    """Search for a word and analyze the first matching row."""
    rows = client.get("/api/search", params={"q": query}).json()["results"]
    row = next(
        (r for r in rows if (form is None or r["form"] == form) and (lemma is None or r["lemma"] == lemma) and (pos is None or r["pos"] == pos)),
        rows[0],
    )
    res = client.get("/api/analyze", params={"id": row["id"]})
    assert res.status_code == 200
    return res.json()


def test_analyze_hacer_tree_is_depth_first_and_enriched():
    data = _analyze_first("hacer", form="hacer", lemma="hacer", pos="verb")
    tree = data["tree"]
    assert tree["root_lemma_id"] is not None
    nodes = tree["nodes"]
    assert len(nodes) == 26
    # frozen contract: depth-first, parent always before child
    seen = set()
    for n in nodes:
        if n["parent_id"] is not None:
            assert n["parent_id"] in seen, f"parent of {n['lemma']} appears after it"
        seen.add(n["lemma_id"])
    root = next(n for n in nodes if n["parent_id"] is None)
    assert root["lemma"] == "hacer" and root["relation"] == "root"
    # the selected entry is flagged
    selected = [n for n in nodes if n["is_selected"]]
    assert len(selected) == 1 and selected[0]["lemma"] == "hacer" and selected[0]["pos"] == "verb"
    # every node carries the enrichment fields
    for n in nodes:
        assert n["pos"] and "gloss" in n and n["form_count"] > 0 and "freq" in n and n["depth"] >= 0
    # the two required multi-level chains
    by_id = {n["lemma_id"]: n for n in nodes}
    by_lemma_pos = {(n["lemma"], n["pos"]): n for n in nodes}
    assert by_lemma_pos[("hacendar", "verb")]["parent_id"] == by_lemma_pos[("hacienda", "noun")]["lemma_id"]
    assert by_lemma_pos[("hacendado", "noun")]["parent_id"] == by_lemma_pos[("hacendar", "verb")]["lemma_id"]
    assert by_lemma_pos[("hechicero", "noun")]["parent_id"] == by_lemma_pos[("hechizo", "noun")]["lemma_id"]
    # depths follow the chains
    assert by_id[tree["root_lemma_id"]]["depth"] == 0
    assert by_lemma_pos[("hacendado", "noun")]["depth"] == 3
    assert by_lemma_pos[("hechicero", "noun")]["depth"] == 2


def test_analyze_satisfacer_ancestry_borrowed_chain():
    data = _analyze_first("satisfacer", form="satisfacer", lemma="satisfacer", pos="verb")
    ancestry = data["ancestry"]
    # payload is newest-first: the word itself, then its etymon chain backwards
    assert [a["word"] for a in ancestry] == ["satisfacer", "satisfacere", "facere"]
    assert [a["lang"] for a in ancestry] == ["es", "la", "la"]
    modes = {a["word"]: a["mode"] for a in ancestry}
    assert modes["satisfacere"] == "borrowed" and modes["facere"] == "derived"
    assert modes["satisfacer"] is None
    assert ancestry[1]["note"] == "satis- + facere"


def test_analyze_hechizo_ancestry_inherited():
    data = _analyze_first("hechizo", form="hechizo", lemma="hechizo", pos="noun")
    ancestry = data["ancestry"]
    assert [a["word"] for a in ancestry] == ["hechizo", "facticius", "facere"]
    assert {a["word"]: a["mode"] for a in ancestry}["facticius"] == "inherited"


def test_analyze_heder_single_node_family_and_empty_ancestry():
    data = _analyze_first("heder")
    assert data["selected"]["lemma"] == "heder"
    nodes = data["tree"]["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["lemma"] == "heder" and nodes[0]["parent_id"] is None
    assert nodes[0]["is_selected"] is True
    assert data["ancestry"] == []
    assert data["cousins"] is None


def test_analyze_echar_cousins_and_ancestry():
    data = _analyze_first("echar", form="echar", lemma="echar", pos="verb")
    assert [a["word"] for a in data["ancestry"]] == ["echar", "iactāre"]
    cousins = data["cousins"]
    assert cousins is not None
    assert cousins["shared_etymon"]["word"] == "iactāre"
    assert "cutoff" in cousins["note"]
    assert [(m["lemma"], m["pos"]) for m in cousins["members"]] == [("proyectar", "verb"), ("objetar", "verb")]
    assert all(m["entry_id"] and m["path"] and m["family_head"] for m in cousins["members"])
    # cousin entry ids must resolve to real analyses (the chips navigate)
    for m in cousins["members"]:
        res = client.get("/api/analyze", params={"id": m["entry_id"]})
        assert res.status_code == 200


def test_analyze_echar_english_relatives_populated():
    # The fixture's echar family carries a real englishRelatives block
    # mirroring the measured option-(b) payload (docs/COGNATES_FEASIBILITY.md).
    data = _analyze_first("echar", form="echar", lemma="echar", pos="verb")
    rel = data["englishRelatives"]
    assert rel is not None
    assert rel["sharedRoot"] == "iactare"
    assert [it["word"] for it in rel["items"]] == [
        "jettison", "jetty", "parge", "parget", "adjection", "subject",
    ]
    for it in rel["items"]:
        assert set(it) == {"word", "gloss", "sharedRoot",
                           "relationType", "explanation", "audio"}
        assert it["audio"] is None
        assert it["relationType"] in ("direct-cognate", "shared-latin-root")
        assert it["sharedRoot"]
    # norm matches are direct cognates and precede the norm_root channel;
    # both channels render with their own shared root.
    assert [it["relationType"] for it in rel["items"]] == [
        "direct-cognate", "direct-cognate", "direct-cognate", "direct-cognate",
        "shared-latin-root", "shared-latin-root",
    ]
    assert all(it["gloss"] for it in rel["items"])


def test_analyze_hacer_english_relatives_null_empty_state():
    # Families without English data keep the §52 empty state (the fixture
    # default), exactly like the sqlite store returns None for hablar.
    data = _analyze_first("hacer", form="hacer", lemma="hacer", pos="verb")
    assert data["englishRelatives"] is None


def test_analyze_mentir_synthesized_star_tree():
    # families without an explicit fixture tree synthesize a star: every
    # non-head member hangs directly off the head
    data = _analyze_first("mentir", form="mentir", lemma="mentir", pos="verb")
    nodes = data["tree"]["nodes"]
    root = next(n for n in nodes if n["parent_id"] is None)
    assert root["lemma"] == "mentir"
    others = [n for n in nodes if n["parent_id"] is not None]
    assert len(others) == len(nodes) - 1
    assert all(n["parent_id"] == root["lemma_id"] for n in others)
    assert all(n["depth"] == 1 for n in others)


# ---------------------------------------------------------------------------
# Phase 1 dashboard keys: query, morphology, familyPreview, origin,
# nearbyForms, word resolution (frozen §D contract, docs
# DESIGN_IMPLEMENTATION_PLAN.md).
# ---------------------------------------------------------------------------

def test_analyze_hacer_morphology_populated():
    data = _analyze_first("hacer", form="hacer", lemma="hacer", pos="verb")
    assert data["query"] == "hacer"
    m = data["morphology"]
    assert m["posLabel"] == "verbo"
    assert m["summary"] == "verbo · no personal · infinitivo"
    assert m["lexeme"] == "hac-"
    assert m["inflection"] == "-er"
    assert m["base"] == "hacer"
    assert m["categoría"] == "verbo"
    assert m["conjugationClass"] == "Segunda (-er)"
    assert m["conjugación"] == "Segunda (-er)"
    assert m["decomposition"] == [
        {"segment": "hac", "label": "raíz o base léxica", "kind": "stem"},
        {"segment": "-er", "label": "desinencia flexiva", "kind": "desinence"},
    ]
    assert m["alternatives"] == []


def test_analyze_summary_accented_tense_matches_mockup():
    # the mockup's grammatical line: imperfect, 1st person plural
    data = _analyze_first("mentíamos", form="mentíamos", lemma="mentir", pos="verb")
    assert data["morphology"]["summary"] == (
        "verbo · modo indicativo · pretérito imperfecto · 1ª persona del plural"
    )
    assert data["morphology"]["lexeme"] == "ment-"
    assert data["morphology"]["inflection"] == "-íamos"
    assert data["morphology"]["conjugationClass"] == "Tercera (-ir)"
    # the decomposition accordion labels the desinence with its grammar
    assert data["morphology"]["decomposition"] == [
        {"segment": "ment", "label": "raíz o base léxica", "kind": "stem"},
        {"segment": "-íamos",
         "label": "desinencia de pretérito imperfecto, 1ª persona del plural",
         "kind": "desinence"},
    ]


def test_analyze_noun_morphology_empty_split():
    # nouns never get a desinence split (the inventory is verbal); the
    # empty state is lexeme/inflection null and an empty decomposition
    data = _analyze_first("mentira", form="mentira", lemma="mentira", pos="noun")
    m = data["morphology"]
    assert m["posLabel"] == "sustantivo"
    assert m["summary"] == "sustantivo · singular"
    assert m["lexeme"] is None and m["inflection"] is None
    assert m["conjugationClass"] is None
    assert m["decomposition"] == []


def test_analyze_origin_from_ancestry():
    # hacer's fixture chain: Spanish hacer ← Latin facere (inherited);
    # stages arrive newest-first per the frozen §D contract
    data = _analyze_first("hacer", form="hacer", lemma="hacer", pos="verb")
    origin = data["origin"]
    assert origin is not None
    assert origin["sourceLanguage"] == "latín"
    assert origin["sourceWord"] == "facere"
    assert origin["sourceMeaning"] is None  # Phase 1: no Latin gloss source (docs F7)
    words = [(s["word"], s["langLabel"]) for s in origin["stages"]]
    assert words == [("hacer", "español"), ("facere", "latín")]


def test_analyze_origin_null_when_no_etymon():
    data = _analyze_first("heder")
    assert data["origin"] is None
    assert data["ancestry"] == []


def test_analyze_family_preview_hub_and_cap():
    data = _analyze_first("hacer", form="hacer", lemma="hacer", pos="verb")
    preview = data["familyPreview"]
    assert preview["hub"] == "hacer"
    assert preview["totalCount"] == 26  # the fixture family's real size
    nodes = preview["nodes"]
    assert nodes[0]["lemma"] == "hacer" and nodes[0]["relationLabel"] == "root"
    assert nodes[0]["isSelected"] is True  # searched the head's citation
    satellites = nodes[1:]
    assert 6 <= len(satellites) <= 10  # docs: hub + 6-10 satellites
    assert all(n["pos"] and "relationLabel" in n and "gloss" in n for n in satellites)
    assert sum(1 for n in nodes if n["isSelected"]) == 1
    # every satellite carries its derivation label (relation-type priority)
    assert all(s["relationLabel"] for s in satellites)


def test_analyze_family_preview_searched_inflected_form_node():
    # searching an inflected form of the head adds a highlighted peripheral
    # node (design.md §18-19): hub mentir + satellite mentíamos
    data = _analyze_first("mentíamos", form="mentíamos", lemma="mentir", pos="verb")
    nodes = data["familyPreview"]["nodes"]
    sel = [n for n in nodes if n["isSelected"]]
    assert len(sel) == 1 and sel[0]["lemma"] == "mentíamos"
    assert nodes[0]["lemma"] == "mentir"


def test_analyze_nearby_forms_present_row_for_infinitive():
    # non-finite searches fall back to the lemma's present-indicative row
    data = _analyze_first("mentir", form="mentir", lemma="mentir", pos="verb")
    forms = [(f["form"], f["features"], f["isLemma"]) for f in data["nearbyForms"]]
    assert [f[0] for f in forms] == ["miento", "mientes", "miente", "mentimos", "mentís", "mienten"]
    assert all("present indicative" in f[1] for f in forms)
    assert all(f[2] is False for f in forms)


def test_analyze_nearby_forms_same_tense_row():
    # searching an imperfect form selects the imperfect paradigm row
    data = _analyze_first("hacía", form="hacía", lemma="hacer", pos="verb")
    forms = [f["form"] for f in data["nearbyForms"]]
    assert "hacía" in forms and all("imperfect" in f["features"] for f in data["nearbyForms"])


def test_analyze_nearby_forms_empty_for_non_verb():
    data = _analyze_first("mentira", form="mentira", lemma="mentira", pos="noun")
    assert data["nearbyForms"] == []


def test_analyze_phase2_phase4_keys_null():
    data = _analyze_first("hacer", form="hacer", lemma="hacer", pos="verb")
    assert data["englishRelatives"] is None
    assert data["mnemonics"] is None
    assert data["selected"]["audio"] is None
    assert data["selected"]["ipa"] is None


def test_analyze_word_param_resolves_top_ranked_with_alternatives():
    # Enter/"Analizar" resolve the exact word to the dropdown's top match;
    # the other lemma of the same surface form surfaces as an alternative
    res = client.get("/api/analyze", params={"word": "mienta"})
    assert res.status_code == 200
    data = res.json()
    assert data["selected"]["lemma"] == "mentir"  # freq 8.7 > mentar 7.5
    alts = data["morphology"]["alternatives"]
    assert [a["lemma"] for a in alts] == ["mentar"]
    assert alts[0]["pos"] == "verb"
    assert alts[0]["summary"]  # a Spanish grammatical line
    # alternative entry ids must resolve to real analyses (they navigate)
    other = client.get("/api/analyze", params={"id": alts[0]["entry_id"]})
    assert other.status_code == 200
    assert other.json()["selected"]["lemma"] == "mentar"


def test_analyze_id_path_also_reports_alternatives():
    data = _analyze_first("mienta", form="mienta", lemma="mentir", pos="verb")
    assert [a["lemma"] for a in data["morphology"]["alternatives"]] == ["mentar"]


def test_analyze_word_param_is_case_and_accent_insensitive():
    res = client.get("/api/analyze", params={"word": "HACER"})
    assert res.status_code == 200
    assert res.json()["selected"]["form"] == "hacer"
    res = client.get("/api/analyze", params={"word": "hacia"})  # → hacía
    assert res.status_code == 200
    assert res.json()["selected"]["form"] == "hacía"


def test_analyze_word_param_requires_exact_match():
    # prefixes must not resolve: "hac" is a fragment, not a word
    res = client.get("/api/analyze", params={"word": "hac"})
    assert res.status_code == 404


def test_analyze_word_param_unknown_word_404():
    res = client.get("/api/analyze", params={"word": "zzznotaword"})
    assert res.status_code == 404


def test_analyze_requires_exactly_one_of_id_or_word():
    res = client.get("/api/analyze")
    assert res.status_code == 422
    res = client.get("/api/analyze", params={"id": "x", "word": "hacer"})
    assert res.status_code == 422
