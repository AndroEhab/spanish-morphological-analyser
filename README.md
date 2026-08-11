# Spanish Morphological Analyser

A web app for exploring Spanish morphology: type into a search box and pick a
dictionary **word form** from the dropdown (there is no free-text submit —
analysis is only ever triggered by selecting a concrete form). The analysis
view shows the selected form's whole morphological/derivational family, grouped
by part of speech, with each member lemma's paradigm rendered in labelled
sections (Non-finite / Indicative / Subjunctive / Imperative / With clitics).

## Screenshots

![hacer family view](scripts/screenshots/10-real-hacer.png)

![mienta ambiguity dropdown](scripts/screenshots/11-real-mienta.png)

![paradigm sections](scripts/screenshots/13-paradigm-sections.png)

## What it does

- **Search-by-form dropdown.** Matching is case- and accent-insensitive and
  tiered: exact form match, then prefix, then (only when the prefix finds
  nothing) substring. Within a tier, results sort by corpus frequency
  descending (multi-word entries carry no frequency and sort last), then by
  length, then alphabetically. Rows for the same surface form under
  different lemmas stay adjacent and are disambiguated with a parenthesised
  lemma qualifier — omitted when it would only repeat the surface form, the
  POS chip and gloss already distinguishing those rows — plus the POS chip
  and the gloss, so `hizo` finds `hizo`, and `mienta` shows both
  `mienta (mentir)` and `mienta (mentar)`.
- **Family analysis.** Each entry resolves to its family: a head lemma, a
  cutoff note when the family has one (explaining why membership ends where
  it does), and groups ordered Verbs → Nouns → Adjectives → Adverbs →
  everything else. Members show a relation chip (`des- + hacer`,
  `inherited from Latin facticius`, `same paradigm as hacer`, …), and their
  forms render as a dense chip grid bucketed into paradigm sections; long
  lists collapse with "show all" toggles.
- **Backends.** The store is a thin dispatcher (`app/store.py`) with two
  implementations exposing the same contract: a hand-authored JSON fixture
  (`app/store_fixture.py`) and the real SQLite store (`app/store_sqlite.py`),
  selected via `MORPH_BACKEND`.

## Source data

The two source datasets are **not** committed to this repository — download
them and place them at the repo root:

- `kaikki.org-dictionary-Spanish.jsonl` — the Spanish extraction from
  <https://kaikki.org/dictionary/Spanish/> (wiktextract output of English
  Wiktionary), ~980 MB
- `SUBTLEX-ESP.xlsx` — SUBTLEX-ESP Spanish subtitle word frequencies, ~3.6 MB

Running `python -m pipeline.build` then produces `data/morph.sqlite`
(~300 MB, ~2 minutes). Until that build has been run, the app falls back to
the bundled JSON fixture.

## Prerequisites

- Python 3.11+ (developed on 3.13).
- The two source data files at the repo root:
  - `kaikki.org-dictionary-Spanish.jsonl` (Wiktionary dump, ~980 MB)
  - `SUBTLEX-ESP.xlsx` (Spanish word frequencies, ~3.6 MB)
- Windows: `py -3` is used below; on other platforms substitute `python3`.

## Setup

```
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
```

## Build the database

The real store reads `data/morph.sqlite` (~300 MB, produced from the source
files above; ~2 minutes):

```
.venv\Scripts\python -m pipeline.build
```

This touches `data/` only (the JSONL intermediates and the SQLite database).
Until it has been run (and while developing), the app falls back to the JSON
fixture.

## Verify

```
.venv\Scripts\python scripts/acceptance.py
```

Runs the read-only acceptance harness (schema/integrity, ambiguity, the hacer
family, non-lemma searchability, family sanity, frequency sanity, API
round-trip). It should report 36 passed, 1 failed — the single failure is a
word genuinely absent from the source dictionary.

## Run

```
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Open <http://localhost:8000/>. The backend is chosen by the `MORPH_BACKEND`
environment variable:

- `auto` (default) — use the SQLite store when `data/morph.sqlite` exists and
  `app/store_sqlite.py` imports cleanly, else the fixture
- `sqlite` — always the SQLite store (fails loudly if unavailable)
- `fixture` — always the JSON fixture (the test suite forces this)

API endpoints:

- `GET /api/search?q=<partial>&limit=<n>` — word-form candidates
- `GET /api/analyze?id=<id>` — family analysis for one entry
- `GET /api/health` — status + entry/lemma/family counts + active backend

## Tests

```
.venv\Scripts\python -m pytest
```

`tests/test_api.py` covers the API contract against the fixture backend
(`MORPH_BACKEND=fixture` is forced by `tests/conftest.py` so the suite is
hermetic); `tests/test_store_sqlite.py` builds a small temporary database with
the exact production schema and tests ranking tiers, group adjacency, POS
ordering, form ordering, homographs, and error paths without touching the real
300 MB database.

## UI smoke test

```
.venv\Scripts\python scripts/ui_smoke.py                 # fixture backend
MORPH_BACKEND=sqlite .venv\Scripts\python scripts/ui_smoke.py   # real backend
```

Drives the real UI with Playwright (headless Chromium; `pip install playwright`
+ `python -m playwright install chromium` first), exercises the full flow —
dropdown, keyboard selection, ambiguity, paradigm sections, clitic expansion,
latency — and captures screenshots to `scripts/screenshots/`.

## Layout

```
app/
  main.py            # FastAPI app: mounts static/, defines API routes
  api.py             # route handlers under /api
  store.py           # backend dispatcher (MORPH_BACKEND)
  store_fixture.py   # fixture-backed store (JSON)
  store_sqlite.py    # SQLite store (production data)
  fixtures/sample.json
  static/            # vanilla HTML/CSS/JS frontend, no build step, no CDN
pipeline/            # linguistic data pipeline (builds data/morph.sqlite)
recon/               # pipeline exploration work
scripts/
  acceptance.py      # read-only acceptance harness
  ui_smoke.py        # Playwright UI verification + screenshots
  screenshots/
tests/
  conftest.py, test_api.py, test_pipeline.py, test_store_sqlite.py
```
