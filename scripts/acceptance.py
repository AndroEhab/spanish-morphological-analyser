"""Acceptance harness for the morphological analyser (read-only).

Usage:
    python scripts/acceptance.py

Runs read-only checks against data/morph.sqlite (plus the SUBTLEX-ESP.xlsx
word list for the vocabulary-match fraction), prints one readable PASS/FAIL
report, and exits 0 only if every check passes. Designed to finish well
under 30 seconds.

Sections:
    A  schema and integrity
    B  ambiguity (mienta / haces / hecho)
    C  the hacer family vs. pipeline/eval/gold_hacer.txt
    D  non-lemma searchability (full dictionary lookup)
    E  family sanity across the lexicon
    F  frequency sanity
    G  API round-trip through app.store_sqlite
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import orjson

ROOT = Path(__file__).resolve().parent.parent
# Running as `python scripts/acceptance.py` puts scripts/ on sys.path[0],
# so the repo root must be added explicitly to import pipeline/app modules.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "morph.sqlite"
GOLD_PATH = ROOT / "pipeline" / "eval" / "gold_hacer.txt"
SUBTLEX_PATH = ROOT / "SUBTLEX-ESP.xlsx"

# Indexes the pipeline build is expected to create (besides sqlite_auto*).
EXPECTED_INDEXES = (
    "form_key_idx",
    "form_lemma_idx",
    "lemma_family_idx",
    "form_key_freq_idx",
    "form_key_freq_form_idx",
)
EXPECTED_TABLES = ("form", "lemma", "family", "meta")

# Machine relation codes that must never surface as a member's label.
MACHINE_RELATION_LABELS = {"affix", "paradigm", "root-key", "derived", "root"}

# Words that must NOT be members of the hacer family.
HACER_EXCLUDED = {
    "factura", "factor", "efecto", "facticio", "faena", "hacha", "hachazo",
    "hachón", "hachar", "hacina", "hacinar", "hacinamiento", "haz", "hazaña",
    "hazañoso", "zaherir", "zaherimiento", "ahechar", "que", "qué", "queísmo",
    "conqué", "pasar", "picar", "sentir",
}

# Non-lemma surfaces that must exist as form rows (full-dictionary lookup).
NON_LEMMA_FORMS = [
    "hizo", "hice", "hecho", "haz", "hacés", "hiciéremos",
    "hacerlo", "haciéndolo", "hazlo", "hagámoslo", "mienta", "mintió",
    "hechicerías",
]

# Families whose full member lists are printed.
FAMILIES_TO_LIST = ["mentir", "decir", "tener", "poner", "casa", "cantar"]

# Words for the search() latency probe.
SEARCH_PROBE = ["ha", "hac", "hacer", "mient", "hiz", "casa"]


class Check:
    """One PASS/FAIL check with optional detail."""

    __slots__ = ("name", "passed", "detail")

    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = bool(passed)
        self.detail = detail


class Harness:
    """Collects checks, prints section headers, computes the verdict."""

    def __init__(self):
        self.checks: list[Check] = []

    def section(self, title: str) -> None:
        print(f"\n=== {title} ===")

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.checks.append(Check(name, passed, detail))
        status = "PASS" if passed else "FAIL"
        line = f"{status}  {name}"
        if detail:
            line += f"  —  {detail}"
        print(line)
        return passed

    def info(self, line: str) -> None:
        print(f"      {line}")

    def summary(self) -> int:
        n_pass = sum(1 for c in self.checks if c.passed)
        n_fail = len(self.checks) - n_pass
        print(f"\n{n_pass} passed, {n_fail} failed")
        return 0 if n_fail == 0 else 1


def connect_ro() -> sqlite3.Connection:
    """Read-only connection; waits out writer locks from pipeline rebuilds."""
    if not DB_PATH.exists():
        raise RuntimeError(f"database not found at {DB_PATH} — the pipeline may be rebuilding")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=20000")
    conn.execute("PRAGMA query_only=ON")
    return conn


def parse_features(raw: str | None) -> list[str]:
    if not raw:
        return []
    parsed = orjson.loads(raw)
    if isinstance(parsed, list):
        return [str(f) for f in parsed]
    return [str(parsed)]


# ---------------------------------------------------------------------------
# A. Schema and integrity
# ---------------------------------------------------------------------------

def section_a(h: Harness, conn: sqlite3.Connection) -> None:
    h.section("A. Schema and integrity")

    tables = {
        r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    missing_tables = [t for t in EXPECTED_TABLES if t not in tables]
    h.check("A1 tables present", not missing_tables,
            f"missing: {missing_tables}" if missing_tables else
            f"found {', '.join(EXPECTED_TABLES)}")

    indexes = {
        r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name NOT LIKE 'sqlite_auto%'"
        )
    }
    missing_idx = [ix for ix in EXPECTED_INDEXES if ix not in indexes]
    h.check("A2 expected indexes present", not missing_idx,
            f"missing: {missing_idx}" if missing_idx else f"found {len(indexes)} indexes")

    n_forms = conn.execute("SELECT COUNT(*) FROM form").fetchone()[0]
    n_lemmas = conn.execute("SELECT COUNT(*) FROM lemma").fetchone()[0]
    n_families = conn.execute("SELECT COUNT(*) FROM family").fetchone()[0]
    h.info(f"row counts: {n_forms} forms, {n_lemmas} lemmas, {n_families} families")
    h.info(f"db size on disk: {DB_PATH.stat().st_size / 1e6:.1f} MB")
    meta = dict(conn.execute("SELECT k, v FROM meta ORDER BY k"))
    h.info(f"meta: {meta}")
    h.info("lemma counts by POS:")
    for r in conn.execute("SELECT pos, COUNT(*) AS n FROM lemma GROUP BY pos ORDER BY n DESC"):
        h.info(f"  {r['pos']:<12} {r['n']}")
    h.info("form counts by lemma POS:")
    for r in conn.execute(
        "SELECT l.pos, COUNT(*) AS n FROM form f JOIN lemma l ON l.id = f.lemma_id "
        "GROUP BY l.pos ORDER BY n DESC"
    ):
        h.info(f"  {r['pos']:<12} {r['n']}")

    n_distinct_pairs = conn.execute(
        "SELECT COUNT(DISTINCT form || x'00' || lemma_id) FROM form"
    ).fetchone()[0]
    h.check("A3 form rows are distinct (form, lemma_id)", n_forms == n_distinct_pairs,
            f"rows={n_forms} distinct pairs={n_distinct_pairs}")

    n_empty = conn.execute("SELECT COUNT(*) FROM form WHERE trim(form) = ''").fetchone()[0]
    # Unicode-aware scan: a surface is "placeholder" when, after stripping
    # whitespace, it has no alphanumeric character at all (bare dashes,
    # punctuation). ASCII GLOB classes would wrongly flag accented letters
    # like "-á" or "é".
    punct_samples: list[str] = []
    n_punct_only = 0
    for (form,) in conn.execute("SELECT form FROM form WHERE trim(form) != ''"):
        if not any(ch.isalnum() for ch in form.strip()):
            n_punct_only += 1
            if len(punct_samples) < 5:
                punct_samples.append(form)
    n_bad_surfaces = n_empty + n_punct_only
    h.check("A4 no empty / whitespace / dash-only surfaces", n_bad_surfaces == 0,
            f"{n_bad_surfaces} bad surface(s) "
            f"({n_empty} empty/whitespace, {n_punct_only} punctuation-only"
            f"{', e.g. ' + repr(punct_samples) if punct_samples else ''})")

    bad_features: list[tuple[int, str]] = []
    for row in conn.execute("SELECT id, features FROM form"):
        raw = row["features"]
        try:
            parsed = orjson.loads(raw)
        except Exception:
            bad_features.append((row["id"], f"unparsable: {raw[:60]!r}"))
            continue
        if not isinstance(parsed, list) or not all(isinstance(f, str) for f in parsed):
            bad_features.append((row["id"], f"not list[str]: {raw[:60]!r}"))
    h.check("A5 every form.features is a JSON array of strings",
            not bad_features,
            f"{len(bad_features)} bad row(s), first: {bad_features[:3]}")

    n_orphan = conn.execute(
        "SELECT COUNT(*) FROM form f LEFT JOIN lemma l ON l.id = f.lemma_id "
        "WHERE l.id IS NULL"
    ).fetchone()[0]
    h.check("A6 zero forms with missing lemma", n_orphan == 0, f"{n_orphan} orphan form(s)")

    n_missing_fam = conn.execute(
        "SELECT COUNT(*) FROM lemma WHERE family_id IS NULL"
    ).fetchone()[0]
    h.check("A7 zero lemmas with missing family_id", n_missing_fam == 0,
            f"{n_missing_fam} lemma(s) without family_id")

    n_formed_missing_fam = conn.execute(
        "SELECT COUNT(*) FROM lemma l WHERE l.family_id IS NULL AND EXISTS "
        "(SELECT 1 FROM form f WHERE f.lemma_id = l.id)"
    ).fetchone()[0]
    h.check("A8 every lemma with forms has a family_id", n_formed_missing_fam == 0,
            f"{n_formed_missing_fam} lemma(s) with forms but no family_id")

    n_no_citation = conn.execute(
        "SELECT COUNT(*) FROM lemma l WHERE NOT EXISTS "
        "(SELECT 1 FROM form f WHERE f.lemma_id = l.id "
        " AND f.form = l.word AND f.is_lemma = 1)"
    ).fetchone()[0]
    h.check("A9 every lemma has a citation-form row (is_lemma=1, form==word)",
            n_no_citation == 0,
            f"{n_no_citation} lemma(s) without their own citation form")


# ---------------------------------------------------------------------------
# B. Ambiguity
# ---------------------------------------------------------------------------

def _form_lemmas(conn: sqlite3.Connection, form: str) -> list[sqlite3.Row]:
    return list(conn.execute(
        "SELECT l.word AS lemma, l.pos AS pos, f.features AS features "
        "FROM form f JOIN lemma l ON l.id = f.lemma_id "
        "WHERE f.form = ? ORDER BY l.word, f.id",
        (form,),
    ))


def _print_form_rows(form: str, rows: list[sqlite3.Row]) -> None:
    for r in rows:
        feats = " · ".join(parse_features(r["features"])) or "(no features)"
        print(f"      {form} | {r['lemma']} ({r['pos']}) | {feats}")


def section_b(h: Harness, conn: sqlite3.Connection) -> None:
    h.section("B. Ambiguity")

    rows = _form_lemmas(conn, "mienta")
    lemmas = sorted({r["lemma"] for r in rows})
    ok = lemmas == ["mentar", "mentir"]
    h.check("B1 mienta resolves to exactly mentir and mentar", ok,
            f"lemmas: {lemmas}")
    _print_form_rows("mienta", rows)

    rows = _form_lemmas(conn, "haces")
    lemmas = sorted({r["lemma"] for r in rows})
    ok = len(lemmas) >= 2 and "hacer" in lemmas and "haz" in lemmas
    h.check("B2 haces shows hacer verb + haz noun plural", ok,
            f"lemmas: {lemmas}")
    _print_form_rows("haces", rows)

    rows = _form_lemmas(conn, "hecho")
    lemmas = sorted({r["lemma"] for r in rows})
    has_adj = any(r["lemma"] == "hecho" and r["pos"] == "adj" for r in rows)
    has_noun = any(r["lemma"] == "hecho" and r["pos"] == "noun" for r in rows)
    has_part = any(
        r["lemma"] == "hacer" and "participle" in " ".join(parse_features(r["features"]))
        for r in rows
    )
    collapsed = len(lemmas) < 2
    ok = (has_adj and has_noun and has_part) and not collapsed
    h.check(
        "B3 hecho shows adjective, noun, and hacer past participle",
        ok,
        f"lemmas: {lemmas} | adj={has_adj} noun={has_noun} participle-of-hacer={has_part} "
        f"| collapsed-to-single-lemma={collapsed}",
    )
    _print_form_rows("hecho", rows)


# ---------------------------------------------------------------------------
# C. The hacer family
# ---------------------------------------------------------------------------

def section_c(h: Harness, conn: sqlite3.Connection) -> None:
    h.section("C. The hacer family")

    gold = [
        line.strip()
        for line in GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    h.info(f"gold: {len(gold)} words from {GOLD_PATH.name}")

    fam_rows = list(conn.execute(
        "SELECT f.id, l.word AS head FROM family f "
        "JOIN lemma l ON l.id = f.head_lemma_id WHERE l.word = 'hacer' "
        "ORDER BY f.id"
    ))
    if not fam_rows:
        h.check("C1 hacer family exists with head hacer", False, "no family headed by 'hacer'")
        return
    fam_id = fam_rows[0]["id"]
    head_ok = fam_rows[0]["head"] == "hacer"
    h.check("C1 family head is hacer", head_ok, f"family {fam_id}")

    members = list(conn.execute(
        "SELECT id, word, pos, relation, relation_label FROM lemma "
        "WHERE family_id = ? ORDER BY (id = (SELECT head_lemma_id FROM family WHERE id = ?)) DESC, word",
        (fam_id, fam_id),
    ))
    form_counts = {
        r["lemma_id"]: r["n"]
        for r in conn.execute(
            "SELECT lemma_id, COUNT(*) AS n FROM form WHERE lemma_id IN "
            f"({','.join('?' * len(members))}) GROUP BY lemma_id",
            [m["id"] for m in members],
        )
    } if members else {}

    print("      members (word | pos | relation_label | form count):")
    for m in members:
        print(
            f"      {m['word']} | {m['pos']} | "
            f"{(m['relation_label'] or '').strip() or '(empty)'} | "
            f"{form_counts.get(m['id'], 0)}"
        )

    member_words = {m["word"] for m in members}
    recall = len(member_words & set(gold)) / len(gold)
    extras = sorted(member_words - set(gold))
    h.info(f"recall vs gold: {recall:.2f} ({len(member_words & set(gold))}/{len(gold)})")
    h.info(f"extras (members not in gold): {extras}")

    h.check("C2 gold recall is complete", member_words >= set(gold),
            f"missing from family: {sorted(set(gold) - member_words) or 'none'}")

    excluded_hits = sorted(member_words & HACER_EXCLUDED)
    h.check("C3 no excluded words in family", not excluded_hits,
            f"present but excluded: {excluded_hits}")

    head_id = conn.execute(
        "SELECT head_lemma_id FROM family WHERE id = ?", (fam_id,)
    ).fetchone()[0]
    bad_labels = [
        (m["word"], (m["relation_label"] or "").strip())
        for m in members
        if m["id"] != head_id
        and (not (m["relation_label"] or "").strip()
             or (m["relation_label"] or "").strip() in MACHINE_RELATION_LABELS)
    ]
    h.check("C4 non-head members have human relation labels", not bad_labels,
            f"offenders: {bad_labels}")


# ---------------------------------------------------------------------------
# D. Non-lemma searchability
# ---------------------------------------------------------------------------

def section_d(h: Harness, conn: sqlite3.Connection) -> None:
    h.section("D. Non-lemma searchability")

    for form in NON_LEMMA_FORMS:
        rows = list(conn.execute(
            "SELECT l.word AS lemma, l.pos AS pos, f.features AS features "
            "FROM form f JOIN lemma l ON l.id = f.lemma_id "
            "WHERE f.form = ? ORDER BY l.word, f.id",
            (form,),
        ))
        if not rows:
            h.check(f"D {form}", False, "ABSENT — no form row exists")
            continue
        feats_by_lemma = {}
        for r in rows:
            feats_by_lemma.setdefault(r["lemma"], set()).update(parse_features(r["features"]))
        desc = "; ".join(
            f"{lemma} [{', '.join(sorted(fs)) or 'no features'}]"
            for lemma, fs in sorted(feats_by_lemma.items())
        )
        h.check(f"D {form}", True, desc)


# ---------------------------------------------------------------------------
# E. Family sanity across the lexicon
# ---------------------------------------------------------------------------

def section_e(h: Harness, conn: sqlite3.Connection) -> None:
    h.section("E. Family sanity across the lexicon")

    sizes = [
        r["n"]
        for r in conn.execute(
            "SELECT family_id, COUNT(*) AS n FROM lemma "
            "WHERE family_id IS NOT NULL GROUP BY family_id"
        )
    ]
    sizes.sort()
    if sizes:
        n = len(sizes)
        median = statistics.median(sizes)
        p95 = sizes[min(n - 1, int(0.95 * n))]
        h.info(
            f"size distribution: min={sizes[0]} median={median:.0f} "
            f"p95={p95} max={sizes[-1]} over {n} families"
        )
    else:
        median = p95 = 0
        h.info("size distribution: no families found")

    big = list(conn.execute(
        "SELECT f.id, l.word AS head, "
        "(SELECT COUNT(*) FROM lemma m WHERE m.family_id = f.id) AS sz "
        "FROM family f JOIN lemma l ON l.id = f.head_lemma_id "
        "ORDER BY sz DESC LIMIT 15"
    ))
    for r in big:
        h.info(f"size {r['sz']:5d}  head {r['head']}")

    oversized = [r["head"] for r in big if r["sz"] > 200]
    oversz = any(r["sz"] > 200 for r in big)
    # also check ALL families, not just top 15
    any_over = any(s > 200 for s in sizes)
    h.check("E1 no family exceeds 200 members", not any_over,
            f"oversized heads: {oversized} (top-15) ; max size {sizes[-1] if sizes else 0}")

    fam_of = {
        r["word"]: r["family_id"]
        for r in conn.execute("SELECT word, family_id FROM lemma WHERE word IN (?, ?, ?)",
                              ("mentir", "sentir", "desmentir"))
    }
    ok = (
        fam_of.get("mentir") is not None
        and fam_of.get("sentir") is not None
        and fam_of["mentir"] != fam_of["sentir"]
        and fam_of.get("desmentir") == fam_of["mentir"]
    )
    h.check("E2 mentir/sentir apart, desmentir with mentir",
            ok, f"family ids: mentir={fam_of.get('mentir')} sentir={fam_of.get('sentir')} "
                f"desmentir={fam_of.get('desmentir')}")

    for word in FAMILIES_TO_LIST:
        row = conn.execute("SELECT family_id FROM lemma WHERE word = ? LIMIT 1", (word,)).fetchone()
        if row is None or row["family_id"] is None:
            h.info(f"{word}: no family")
            continue
        words = [r["word"] for r in conn.execute(
            "SELECT word FROM lemma WHERE family_id = ? ORDER BY word", (row["family_id"],)
        )]
        if len(words) > 200:
            shown = ", ".join(words[:40]) + f", ... and {len(words) - 40} more"
        else:
            shown = ", ".join(words)
        h.info(f"{word} family ({row['family_id']}, {len(words)} members): {shown}")

    n_singleton = sum(1 for s in sizes if s == 1)
    total_in_singletons = sum(s for s in sizes if s == 1)
    total_familied = conn.execute(
        "SELECT COUNT(*) FROM lemma WHERE family_id IS NOT NULL"
    ).fetchone()[0]
    frac = total_in_singletons / total_familied if total_familied else 0.0
    h.info(
        f"singleton families: {n_singleton} ({n_singleton / len(sizes):.1%} of families) "
        f"covering {total_in_singletons} lemmas ({frac:.1%} of familied lemmas)"
    )


# ---------------------------------------------------------------------------
# F. Frequency sanity
# ---------------------------------------------------------------------------

def section_f(h: Harness, conn: sqlite3.Connection) -> None:
    h.section("F. Frequency sanity")

    n_pos = conn.execute("SELECT COUNT(*) FROM form WHERE freq > 0").fetchone()[0]
    h.info(f"forms with freq > 0: {n_pos}")

    try:
        from pipeline.frequency import load as load_subtlex
        subtlex = load_subtlex(SUBTLEX_PATH)
    except Exception as exc:  # pragma: no cover
        h.check("F1 SUBTLEX vocabulary match", False, f"could not load SUBTLEX: {exc}")
        subtlex = {}
    else:
        db_forms = {r[0].lower() for r in conn.execute("SELECT form FROM form")}
        matched = len(subtlex.keys() & db_forms)
        frac = matched / len(subtlex) if subtlex else 0.0
        h.check("F1 SUBTLEX vocabulary matched", True,
                f"{matched}/{len(subtlex)} = {frac:.1%} of SUBTLEX words appear as forms")

    sample = [r["id"] for r in conn.execute("SELECT id FROM lemma ORDER BY RANDOM() LIMIT 200")]
    if sample:
        placeholders = ",".join("?" * len(sample))
        lemma_freq = {
            r["id"]: r["freq"] for r in conn.execute(
                f"SELECT id, freq FROM lemma WHERE id IN ({placeholders})", sample
            )
        }
        max_form_freq = {
            r["lemma_id"]: r["m"] for r in conn.execute(
                f"SELECT lemma_id, MAX(freq) AS m FROM form "
                f"WHERE lemma_id IN ({placeholders}) GROUP BY lemma_id", sample
            )
        }
        mismatches = [
            (lid, lemma_freq.get(lid, 0.0), max_form_freq.get(lid, 0.0))
            for lid in sample
            if abs((lemma_freq.get(lid, 0.0) or 0.0) - (max_form_freq.get(lid, 0.0) or 0.0)) > 1e-9
        ]
        h.check("F2 lemma.freq == MAX(form.freq) on 200 random lemmas",
                not mismatches, f"{len(mismatches)} mismatches, first: {mismatches[:3]}")
    else:
        h.check("F2 lemma.freq == MAX(form.freq)", False, "no lemmas to sample")

    top = list(conn.execute("SELECT form, freq FROM form ORDER BY freq DESC, form LIMIT 20"))
    h.info("top 20 forms by freq:")
    for r in top:
        h.info(f"  {r['form']:<22} {r['freq']:.4f}")


# ---------------------------------------------------------------------------
# G. API round-trip
# ---------------------------------------------------------------------------

def section_g(h: Harness) -> None:
    h.section("G. API round-trip (app.store_sqlite)")

    try:
        from app.store_sqlite import analyze, search
    except Exception as exc:  # pragma: no cover
        h.check("G0 import app.store_sqlite", False, str(exc))
        return

    res = search("mient", 25)
    mienta = [r for r in res if r["form"] == "mienta"]
    idx = [i for i, r in enumerate(res) if r["form"] == "mienta"]
    adjacent = len(idx) == 2 and idx[1] - idx[0] == 1
    quals = [r["qualifier"] for r in mienta]
    ok = (
        len(mienta) == 2
        and adjacent
        and all(q is not None for q in quals)
        and len(set(quals)) == 2
    )
    h.check("G1 search('mient', 25) returns both mienta rows adjacent with distinct qualifiers",
            ok,
            f"rows={[(r['lemma'], r['qualifier']) for r in mienta]} indices={idx}")

    res = search("hacer", 25)
    h.check("G2 search('hacer', 25)[0].form == 'hacer'",
            bool(res) and res[0]["form"] == "hacer",
            f"top result: {res[0]['form'] if res else '(none)'} ({res[0]['lemma'] if res else ''})")

    hacer_row = next((r for r in res if r["form"] == "hacer" and r["lemma"] == "hacer"), None)
    if hacer_row is None:
        h.check("G3 analyze(hacer infinitive) groups start with verb, verb group has satisfacer",
                False, "no 'hacer' (lemma hacer) row in search('hacer', 25)")
    else:
        view = analyze(hacer_row["id"])
        if view is None:
            h.check("G3 analyze(hacer infinitive)", False, "analyze returned None")
        else:
            groups = view["family"]["groups"]
            first = groups[0] if groups else None
            verb_lemmas = [m["lemma"] for m in first["members"]] if first else []
            ok = bool(first) and first["pos"] == "verb" and "satisfacer" in verb_lemmas
            h.check(
                "G3 analyze(hacer infinitive) groups start with verb, verb group has satisfacer",
                ok,
                f"first group pos={first['pos'] if first else '(none)'} "
                f"verb members={verb_lemmas[:12]}"
                f"{' ...' if len(verb_lemmas) > 12 else ''}",
            )

    h.check("G4 analyze(unknown id) returns None",
            analyze("999999999999") is None,
            "returned non-None" if analyze("999999999999") is not None else "None")

    latencies = []
    for q in SEARCH_PROBE:
        t0 = time.perf_counter()
        search(q, 25)
        latencies.append(time.perf_counter() - t0)
    p50 = statistics.median(latencies)
    h.info(f"search latency p50 over {SEARCH_PROBE}: {p50 * 1000:.1f} ms "
           f"(per-query: {', '.join(f'{t * 1000:.1f}' for t in latencies)} ms)")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.perf_counter()
    h = Harness()
    print("Acceptance harness — morphological analyser (read-only)")
    print(f"db: {DB_PATH}")

    try:
        conn = connect_ro()
    except Exception as exc:
        h.section("A. Schema and integrity")
        h.check("A0 database available", False, str(exc))
        return h.summary()

    try:
        section_a(h, conn)
        section_b(h, conn)
        section_c(h, conn)
        section_d(h, conn)
        section_e(h, conn)
        section_f(h, conn)
        conn.close()
        section_g(h)
    except sqlite3.OperationalError as exc:
        h.check("RUN ERROR", False, f"database operation failed (concurrent rebuild?): {exc}")
    except Exception as exc:  # pragma: no cover
        h.check("RUN ERROR", False, f"unexpected error: {exc!r}")

    elapsed = time.perf_counter() - t0
    print(f"\n(elapsed {elapsed:.1f}s)")
    return h.summary()


if __name__ == "__main__":
    sys.exit(main())
