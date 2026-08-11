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
