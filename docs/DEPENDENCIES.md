# Dependency Audit — Spanish Morphological Analyser

Audit date: 2026-08-12. Windows 11, Python 3.13, venv at `.venv`.
Audit method: AST import scan of every `.py` file under `app/`, `pipeline/`,
`scripts/`, `tests/`, `recon/`; `pip list` of the venv; `importlib.metadata`
for the dependency tree; live server exercise with the source datasets
removed; pytest under both backends.

## 1. Dependency table

Every third-party package the project actually imports, plus everything
declared in `requirements.txt` (runtime + build) and `requirements-dev.txt`
(tests + UI smoke, see §9).

| Package | Version | Scope | Imported by | Why it is needed |
|---|---|---|---|---|
| `fastapi` | 0.141.1 | runtime | `app/main.py` (`FastAPI`, `StaticFiles`), `app/api.py` (`APIRouter`, `HTTPException`, `Query`) | Web framework: app object, `/api` routes, static mount. Tests use it too via `fastapi.testclient.TestClient` (`tests/test_api.py`). |
| `uvicorn` | 0.52.1 | runtime | no project file imports it — launched as `python -m uvicorn app.main:app` | ASGI server. Declared as plain `uvicorn` since the 2026-08-12 split; the `[standard]` extra is unused (see §2). |
| `orjson` | 3.11.9 | runtime (sqlite backend) + dev | `app/store_sqlite.py:36` (`orjson.loads` on the `form.features` JSON column), `scripts/acceptance.py`, `recon/extract_samples.py` | Fast JSON parsing of the features array — hot path for family views. Runtime dependency of the production backend. |
| *(removed 2026-08-12)* | | | — | Was the SUBTLEX-ESP xlsx reader (`pipeline/frequency.py:13`), build only. Removed with the FrequencyWords swap — the new loader is stdlib-only, so `openpyxl` is gone from `requirements.txt`. |
| `pytest` | 9.1.1 | dev only | `tests/test_pipeline.py`, `tests/test_store_sqlite.py` | Test runner. |
| `httpx` | 0.28.1 | dev only (transitive) | **no project file imports it** | Declared in `requirements-dev.txt` (deliberately — see the comment there) but never imported directly. It is a real requirement of the test suite: `starlette.testclient.TestClient` (which `fastapi.testclient` re-exports) is built on httpx — pytest emits a `StarletteDeprecationWarning` about it. Not needed at runtime. |
| `playwright` | 1.62.0 | dev only | `scripts/ui_smoke.py:18` | Headless-Chromium UI smoke test. Declared in `requirements-dev.txt` since 2026-08-12; before the split it was the only used-but-undeclared package (reproducibility bug — anyone cloning the repo could not run `scripts/ui_smoke.py`). |

Stdlib-only modules (no third-party imports at all): `pipeline/normalize.py`,
`pipeline/etymology.py`, `pipeline/extract.py`, `pipeline/family.py`,
`pipeline/paradigm.py`, `pipeline/tags.py`, `pipeline/subset.py`,
`pipeline/frequency.py`, `pipeline/build.py`, `app/store.py`,
`app/store_fixture.py`, `tests/conftest.py`, `tests/test_api.py` (apart
from fastapi).

### Declared-but-unused
- `httpx` — in `requirements-dev.txt`, imported by zero project files. Needed
  only as a transitive dependency of starlette's `TestClient` when running
  the tests. Kept deliberately (with a comment in the requirements file), but
  it is not a runtime dependency and is not used directly.

### Used-but-undeclared (resolved 2026-08-12)
- `playwright` — imported by `scripts/ui_smoke.py`. It was absent from
  `requirements.txt` (the only used-but-undeclared package); the requirements
  split (§9) now declares it in `requirements-dev.txt`. All other third-party
  imports are declared.

## 2. Installed third-party packages and the transitive tree

Full `pip list` of the venv (34 entries incl. pip): `annotated-doc 0.0.5`,
`annotated-types 0.8.0`, `anyio 4.14.2`, `certifi 2026.7.22`, `click 8.4.2`,
`colorama 0.4.6`, `et_xmlfile 2.0.0`, `fastapi 0.141.1`, `greenlet 3.5.5`,
`h11 0.16.0`, `httpcore 1.0.9`, `httptools 0.8.0`, `httpx 0.28.1`,
`idna 3.18`, `iniconfig 2.3.0`, `openpyxl 3.1.5`, `orjson 3.11.9`,
`packaging 26.3`, `playwright 1.62.0`, `pluggy 1.6.0`, `pydantic 2.13.4`,
`pydantic_core 2.46.4`, `pyee 13.0.1`, `Pygments 2.20.0`, `pytest 9.1.1`,
`python-dotenv 1.2.2`, `PyYAML 6.0.3`, `starlette 1.6.0`,
`typing_extensions 4.16.0`, `typing-inspection 0.4.3`, `uvicorn 0.52.1`,
`watchfiles 1.2.0`, `websockets 17.0.1`.

Relevant edges (from package metadata):

- `fastapi` → starlette, pydantic, typing-extensions, typing-inspection, annotated-doc
- `starlette` → anyio, typing-extensions
- `pydantic` → pydantic-core, annotated-types, typing-extensions, typing-inspection
- `anyio` → idna (sniffio/exceptiongroup no longer pulled on Python 3.13)
- `uvicorn` (base) → click, h11, typing-extensions
- `pytest` → colorama (win32), iniconfig, packaging, pluggy, pygments
- `openpyxl` → et-xmlfile
- `httpx` → anyio, certifi, httpcore, idna
- `playwright` → pyee, greenlet

**`uvicorn[standard]` extras** — the bracket pulls httptools, python-dotenv,
PyYAML, uvloop (not installable on Windows, skipped), watchfiles, websockets,
and colorama (via click). All except uvloop are installed. The application
needs **none** of them: it uses no WebSocket endpoints (websockets), no
`--reload`/watchfiles at runtime, no `--env-file` (python-dotenv/PyYAML), and
no httptools event loop. `uvicorn[standard]` is overkill; plain `uvicorn`
would suffice. `Pygments` is pulled by pytest 9 (not by uvicorn). As of the
2026-08-12 split, `requirements.txt` declares plain `uvicorn`, so none of
these extras are installed in a fresh runtime install (verified in §9).

## 3. Frontend network surface

`app/static/` (index.html, app.js, styles.css) was scanned for
`http://`, `https://`, `cdn`, `unpkg`, `googleapis`, `<script src=`,
`@import`, `url(`. Results:

- `index.html` references only relative assets: `<link rel="stylesheet"
  href="styles.css">` and `<script src="app.js">`. No fonts, no CDN, no icons.
- `app.js` contains exactly two network calls, both same-origin relative
  URLs: `fetch("/api/search?...")` (line 242) and `fetch("/api/analyze?...")`
  (line 676).
- `styles.css` has no `url(`/`@import`/remote font references.

**Verdict: the frontend is genuinely offline-capable — zero external
requests** beyond the same-origin `/api` calls that the server itself
answers.

## 4. External datasets

| Dataset | Size on disk | Licence | Needed at runtime? |
|---|---|---|---|
| `kaikki.org-dictionary-Spanish.jsonl` (wiktextract extraction of the Spanish section of English Wiktionary, kaikki.org) | 1,026,541,959 B (~979 MB) | CC BY-SA 4.0 and GFDL (kaikki.org: "same licenses as Wiktionary"; Wiktionary dual-licensed CC BY-SA 4.0 + GFDL — see docs/LICENSES.md) | **No** |
| `es_full.txt` (hermitdave/FrequencyWords Spanish frequency list, OpenSubtitles-derived) | 14,547,688 B (~14.5 MB) | CC BY-SA 4.0 ("MIT License for code. CC-by-sa-4.0 for content." per the repository — see docs/LICENSES.md §2b) | **No** |

Both are consumed only at build time by `pipeline/build.py`
(`JSONL_PATH`/`FREQ_PATH` at `pipeline/build.py:25-26`, fed into
`pipeline.frequency.load`). `pipeline/subset.py` also reads the kaikki
JSONL, but only as a dev tool. (The superseded `SUBTLEX-ESP.xlsx` still sits
untracked at the repo root but nothing reads it — see docs/LICENSES.md §2a.)

What happens without them:

- **Serving the app: nothing.** With `data/morph.sqlite` present, all
  endpoints answer identically (see §5).
- **Rebuilding the DB: impossible** — `python -m pipeline.build` hard-fails
  without both files.
- **`scripts/acceptance.py`: check F1 fails** (see §5) — it re-reads
  `es_full.txt` live for a vocabulary-coverage fraction.
- **`pytest`: one test skips** gracefully (`pytest.skip("es_full.txt not
  present")`, `tests/test_pipeline.py`).

## 5. Empirical independence test (Part B) — actual output

Procedure: renamed `kaikki.org-dictionary-Spanish.jsonl` →
`.jsonl.away` and `SUBTLEX-ESP.xlsx` → `.xlsx.away` (moved out of the repo
root, nothing deleted), ran the checks, then restored and verified sizes.

### 5.1 Server, `MORPH_BACKEND=sqlite`, datasets absent

```
$ .venv/Scripts/python -m uvicorn app.main:app --port 8010   # MORPH_BACKEND=sqlite
Application startup complete

$ curl -s http://127.0.0.1:8010/api/health
{"status":"ok","backend":"sqlite","entries":1256152,"lemmas":117253,"families":88420}

$ curl -s "http://127.0.0.1:8010/api/search?q=hacer&limit=25"
{"query":"hacer","results":[{"id":"672182","form":"hacer","lemma":"hacer","pos":"verb",
 "label":"hacer","gloss":"to do, perform, execute, carry out","freq":1827.8125,
 "is_lemma":true,"features":["infinitive"],"qualifier":"hacer"},{"id":"672183", ...},

$ curl -s "http://127.0.0.1:8010/api/search?q=mienta&limit=25"
{"query":"mienta","results":[{"id":"817240","form":"mienta","lemma":"mentar","pos":"verb", ...},
 {"id":"817239","form":"mienta","lemma":"mentir","pos":"verb", ...}]}

$ curl -s "http://127.0.0.1:8010/api/analyze?id=672182"
{"selected":{"id":"672182","form":"hacer","lemma":"hacer","pos":"verb",
 "gloss":"to do, perform, execute, carry out","features":["infinitive"]},
 "family":{"head":{"lemma":"hacer","pos":"verb",...},"note":null,
 "groups":[{"pos":"verb","pos_label":"Verbs","members":[{"lemma":"hacer", ... satisfacer ...
 deshacer ... rehacer ... contrahacer ...}]}]}}

$ curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8010/api/analyze?id=672182"   # 200
$ curl -s "http://127.0.0.1:8010/api/analyze?id=nonexistent123"
{"detail":"no entry for id 'nonexistent123'"}    # HTTP 404
```

Every endpoint — health, both searches (hacer; the mienta/mentar–mentir
ambiguity), a full family analysis, and the 404 path — works with the
datasets gone.

### 5.2 `python scripts/acceptance.py`, datasets absent

```
35 passed, 2 failed        (exit code 1)
```

- **F1 FrequencyWords vocabulary match — FAIL**
  `could not load FrequencyWords: [Errno 2] No such file or directory:
  'D:\morphological analyser\es_full.txt'`
  — this is the hidden dependency: `scripts/acceptance.py:506-508` imports
  `pipeline.frequency.load` and re-reads `es_full.txt` live. Baseline
  (datasets present) is 36 passed / 1 failed per the README; the extra
  failure is exactly F1. The other failure, C2 "gold recall is complete
  (malhecho)", is the pre-existing, documented, data-inherent gap — it fails
  with or without the datasets.

- All other sections — schema/integrity (A), ambiguity (B), the hacer family
  (C, apart from C2), non-lemma searchability (D), family sanity (E), F2
  frequency invariants, API round-trip (G) — pass using only
  `data/morph.sqlite`.

### 5.3 `pytest`, datasets absent

```
$ .venv/Scripts/python -m pytest -q            # MORPH_BACKEND=fixture (conftest default)
65 passed, 1 skipped, 1 warning in 1.16s       # exit 0

$ MORPH_BACKEND=sqlite .venv/Scripts/python -m pytest -q
65 passed, 1 skipped, 1 warning in 1.18s       # exit 0
```

The single skip is `tests/test_pipeline.py`'s frequency test, which
explicitly skips when `es_full.txt` is absent (graceful degradation,
not a failure). The 1 warning is starlette's deprecation notice about
`TestClient` being built on httpx.

### 5.4 Restoration

```
kaikki.org-dictionary-Spanish.jsonl  1026541959 bytes   (matches original, ~979 MB)
SUBTLEX-ESP.xlsx                        3763108 bytes   (matches original, ~3.6 MB)
```

Both files restored to their original names, byte-identical sizes; no
`.away` files remain.

### 5.5 Part B verdict

**The serving application does not need the two source datasets at all once
`data/morph.sqlite` exists.** Its only file reads are `data/morph.sqlite`
(sqlite backend) and `app/fixtures/sample.json` (fixture backend) — verified
by grep across `app/` (`open(`, `read_text`, `jsonl`, `.xlsx` hit nothing
else). There are **no hidden reads in the app**. The datasets are needed only
by: the DB build (`pipeline/build.py`), the acceptance harness check F1, and
the frequency unit test (which skips). If you ever delete the datasets, only
those three dev/build paths are affected.

## 6. App → pipeline coupling (Part C)

- The **only** import from `app/` into `pipeline/` is
  `app/store_sqlite.py:38` — `from pipeline.normalize import fold as _fold`.
  (Grep for `pipeline` across `app/` confirms: every other hit is prose in a
  docstring or comment.)
- Symbol crossing the boundary: exactly one — `fold` (accent/case folding for
  accent-insensitive matching).
- `pipeline/normalize.py` is **2,083 bytes** and imports **only stdlib**
  (`re`, `unicodedata`) — the coupling is cheap: importing it drags no
  third-party pipeline dependencies into the runtime. (Importing
  `pipeline.normalize` does require `pipeline/__init__.py` to exist; it is
  present and empty.)
Note the reverse: `app/store_sqlite.py` also imports `orjson` (§1), so the
runtime's third-party surface is `fastapi` + `uvicorn` + `orjson` + their
transitive closures; `openpyxl` never crosses into `app/`.

**Design decision (recorded 2026-08-12, deliberately not changed):** the
`app → pipeline.normalize.fold` import stays as is. The DB stores a
pre-folded `form.key` at build time, and at query time the app must fold the
user's input with the *identical* function — if the two ever drifted,
accent-insensitive search (`hacér` → `hacer`) would silently break. The
shared 2 KB pure-stdlib module guarantees byte-identical folding by
construction. Duplicating `fold()` into `app/` would save a tiny coupling at
the price of a real correctness risk, so this is a deliberate trade-off, not
an oversight.

### Minimal file set to run the app (not build the DB)

| File | Bytes |
|---|---|
| `app/__init__.py` | 0 |
| `app/main.py` | 616 |
| `app/api.py` | 836 |
| `app/store.py` | 1,896 |
| `app/store_fixture.py` | 8,507 |
| `app/store_sqlite.py` | 18,496 |
| `app/fixtures/sample.json` | 261,667 |
| `app/static/index.html` | 1,562 |
| `app/static/app.js` | 26,678 |
| `app/static/styles.css` | 12,058 |
| `pipeline/__init__.py` | 0 |
| `pipeline/normalize.py` | 2,083 |
| **Total (excl. `data/morph.sqlite`)** | **334,399 B ≈ 0.33 MB** |

- `data/morph.sqlite` on disk: **309,768,192 bytes (295.4 MiB)**.
- `store_fixture.py` + `sample.json` are only exercised in `fixture`/`auto`
  fallback mode; if you pin `MORPH_BACKEND=sqlite` they are not needed, and
  the set shrinks to ~72.7 KB of code (the six `app/*.py` + static + the two
  `pipeline/` files). `store.py` imports the fixture module lazily inside a
  branch, so it never loads in `sqlite` mode.

## 7. External services / network (Part D)

Grep of `app/` for `requests`, `urllib`, `httpx`, `aiohttp`, `socket`,
`fetch(`, `urlopen`, `http://`, `https://`:

- Python side (`app/*.py`): **zero hits** — no telemetry, no model API, no
  analytics, no outbound socket.
- Frontend: only the two same-origin `fetch("/api/...")` calls (§3).
- `scripts/ui_smoke.py` uses `urllib.request` solely to poll
  `http://127.0.0.1:8011/api/health` while its dev-only smoke test starts a
  local server — loopback, dev tooling, not part of the app.

**Verdict: the running application makes zero outbound network calls.**

## 8. If you wanted a fully self-contained distribution

Accurate statement of what would have to change (not implemented):

1. **Runtime requirements**: split dev/build deps out of the runtime set —
   the server only needs `fastapi`, `uvicorn` (plain, drop `[standard]`),
   `orjson` and their transitive closures; `openpyxl` (build), `pytest` +
   `httpx` (dev), `playwright` (dev) move to a dev requirements file.
   Pin exact versions. — **Done 2026-08-12**: the split into
   `requirements.txt` / `requirements-dev.txt` landed with this document
   (see §9); pinning exact versions remains open.
2. **Ship the data**: either bundle `data/morph.sqlite` (295.4 MB) or keep a
   documented build step; the two raw datasets (~983 MB) stay out of any
   distribution. The DB is derived from CC BY-SA 4.0/GFDL Wiktionary data (see
   docs/LICENSES.md) and FrequencyWords frequencies (CC BY-SA 4.0), so a
   redistributed build carries attribution/SHARE-ALIKE obligations — but,
   since the 2026-08-12 swap, no non-commercial/no-derivatives restrictions.
3. **Kill the app→pipeline coupling**: `pipeline/normalize.py` is 2 KB of
   pure stdlib; inlining `fold` into `app/` (or moving normalize.py into
   `app/`) would make `app/` self-contained. The pipeline would keep its own
   copy or `app` would export it — a small refactor either way.
4. **Optional**: remove the fixture fallback (or keep it — it is only
   `sample.json`, 262 KB), drop `recon/` and `scripts/` from any shipped
   artifact, and document `MORPH_BACKEND=sqlite` as the only supported mode.
5. A frozen single-binary (PyInstaller/Nuitka) is possible — the runtime is
   pure Python + `orjson` (has wheels) + the static files — but is a bigger
   change than the four points above.

## 9. Requirements split + clean-install verification (2026-08-12)

Following the audit, the single `requirements.txt` was split into two files
that map to real user journeys:

- `requirements.txt` — everything needed to **build the DB and run the app**:
  `fastapi`, `uvicorn` (plain — the `[standard]` extra was dropped; a comment
  in the file explains it only buys `--reload`/watchfiles for development),
  `orjson`. (`openpyxl` was removed 2026-08-12 with the FrequencyWords
  swap — it existed only to read SUBTLEX-ESP.xlsx.)
- `requirements-dev.txt` — tests and the UI smoke, on top of
  `requirements.txt`: `pytest`, `httpx`, `playwright`. `httpx` is kept with a
  comment explaining it is required by starlette's `TestClient` even though
  no project file imports it, so nobody removes it later and breaks the suite.
  `playwright` (previously used-but-undeclared, the reproducibility bug) is
  now declared here.

**Clean-install proof** (throwaway `.venv-check`, Python 3.13.5, deleted
afterwards — the real `.venv` was not touched):

```
$ py -3 -m venv .venv-check
$ .venv-check/Scripts/python -m pip install -r requirements.txt
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.14.2
click-8.4.2 colorama-0.4.6 et_xmlfile-2.0.0 fastapi-0.141.1 h11-0.16.0
idna-3.18 openpyxl-3.1.5 orjson-3.11.9 pydantic-2.13.4 pydantic-core-2.46.4
starlette-1.6.0 typing-extensions-4.16.0 typing-inspection-0.4.3
uvicorn-0.52.1
# -> exactly the runtime/build set: NO httptools, python-dotenv, PyYAML,
#    watchfiles, websockets (uvicorn extras), and NO pytest/httpx/playwright.

$ .venv-check/Scripts/python -c "import pipeline.build; import app.main; print('pipeline.build + app.main import OK')"
pipeline.build + app.main import OK

$ MORPH_BACKEND=sqlite .venv-check/Scripts/python -m uvicorn app.main:app --port 8012
# (full rebuild NOT run — importing the build module and serving is the gate)
$ curl -s http://127.0.0.1:8012/api/health
{"status":"ok","backend":"sqlite","entries":1256152,"lemmas":117253,"families":88420}
$ curl -s "http://127.0.0.1:8012/api/search?q=hacer&limit=3"   # full rows, id 672182 ...

$ .venv-check/Scripts/python -m pip install -r requirements-dev.txt
Successfully installed certifi-2026.7.22 greenlet-3.5.5 httpcore-1.0.9
httpx-0.28.1 iniconfig-2.3.0 packaging-26.3 playwright-1.62.0 pluggy-1.6.0
pyee-13.0.1 pygments-2.20.0 pytest-9.1.1

$ .venv-check/Scripts/python -m pytest -q
66 passed, 1 warning in 3.59s        # exit 0
```

**Result: the split is correct — the clean install exposed no missing
package.** `requirements.txt` alone imports the whole build pipeline and the
app, and serves the real SQLite-backed API; adding `requirements-dev.txt`
makes the full suite pass (66 passed; the SUBTLEX frequency test ran rather
than skipped because the datasets were present in this run). `.venv-check`
was deleted afterwards.
