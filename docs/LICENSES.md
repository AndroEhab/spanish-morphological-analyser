# Licenses & Attribution — Spanish Morphological Analyser

Audit date: 2026-08-12. Verified from package metadata (`importlib.metadata`),
the primary sources over the network (kaikki.org, en.wiktionary.org,
foundation.wikimedia.org, the Ghent University CRR archive), and the git tree
of this repository. **This is a factual audit**: it reports what each licence
text says, quotes the terms verbatim, and states the obligations that plainly
follow from reading those texts. It is **not legal advice** — for a binding
determination of what these licences require in a specific jurisdiction or
use, consult a lawyer qualified in your jurisdiction.

## Plain-language summary

**What must be credited, in one paragraph:** This repository does not ship
its two source datasets and does not vendor any third-party code, so the ~33
pip-installed Python packages (all MIT/BSD/Apache/PSF permissive, plus two
MPL-2.0 weak-copyleft, **no GPL/AGPL**) trigger **no** attribution duty for
publishing this source repo as it stands — only if a frozen artifact that
*contains* their code (PyInstaller binary, Docker image, wheel) is shipped,
which would require carrying their licence notices. The data is the real
story: word data derives from English Wiktionary via kaikki.org and is
dual-licensed **CC BY-SA 4.0 + GFDL** (the README previously claimed 3.0 —
corrected in this audit); the frequency data was **SUBTLEX-ESP, licensed CC
BY-NC-ND 3.0**
(non-commercial, no-derivatives) — a materially restrictive finding, since
the pipeline merged SUBTLEX values into the built database. **That finding
was acted on (2026-08-12): SUBTLEX-ESP was replaced with the
hermitdave/FrequencyWords OpenSubtitles frequency list, licensed CC BY-SA
4.0** ("MIT License for code. CC-by-sa-4.0 for content." per the
repository), so the built database is now a single uniformly CC BY-SA 4.0
derivative and is distributable under that licence (see §2 and Part C —
the SUBTLEX NC/ND history is preserved as a superseded note). The tracked
fixture `app/fixtures/sample.json` is the one committed artifact with
external data, but it is **not** frequency-source-exposed: mechanically
verified, its 1,259 frequency values are hand-invented demo numbers (all
round to one decimal, zero match the real FrequencyWords per-million values
in the built DB), and its 46 glosses are *abridged/lightly reworded*
Wiktionary glosses (one verbatim) — so CC BY-SA attribution is due today,
and nothing NC/ND-licensed attaches to this repository or its build output
anymore. Finally, this repository's own code is licensed **MIT (© 2026
AndroEhab)** — see `LICENSE` at the repo root — while the embedded
dictionary content remains **CC BY-SA 4.0** (see `LICENSE-DATA.md` and the
Repository licensing status section below).

---

## Part A — Software dependencies (all installed via pip, none vendored)

Method: `importlib.metadata` over the venv (Python 3.13, Windows), reading
the declared `License` field, PEP 639 `License-Expression`, and `License ::`
trove classifiers, plus the installed LICENSE files for the edge cases.
34 distributions installed incl. `pip` (33 third-party packages).

| Package | Version | Declared licence (metadata) | Family | Notes |
|---|---|---|---|---|
| `annotated-doc` | 0.0.5 | MIT (License-Expression) | permissive | |
| `annotated-types` | 0.8.0 | MIT (+ classifier) | permissive | |
| `anyio` | 4.14.2 | MIT | permissive | |
| `certifi` | 2026.7.22 | **MPL-2.0** (`License` field + classifier) | **weak copyleft** | your recollection confirmed |
| `click` | 8.4.2 | BSD-3-Clause | permissive | |
| `colorama` | 0.4.6 | BSD (classifier); LICENSE.txt is BSD-3-Clause text | permissive | licence field empty, text verified |
| `et_xmlfile` | 2.0.0 | MIT (+ classifier) | permissive | |
| `fastapi` | 0.141.1 | MIT | permissive | |
| `greenlet` | 3.5.5 | **MIT AND PSF-2.0** (License-Expression) | permissive | PSF-2.0 covers Stackless-Python-derived platform files (LICENSE.PSF shipped) |
| `h11` | 0.16.0 | MIT (+ classifier) | permissive | |
| `httpcore` | 1.0.9 | BSD-3-Clause (+ classifier) | permissive | |
| `httptools` | 0.8.0 | MIT (License-Expression) | permissive | |
| `httpx` | 0.28.1 | BSD-3-Clause (+ classifier) | permissive | |
| `idna` | 3.18 | BSD-3-Clause | permissive | |
| `iniconfig` | 2.3.0 | MIT | permissive | |
| `openpyxl` | 3.1.5 | MIT (+ classifier) | permissive | |
| `orjson` | 3.11.9 | **MPL-2.0 AND (Apache-2.0 OR MIT)** (License-Expression) | **weak copyleft component** | not the plain dual MIT/Apache you believed; ships LICENSE-MPL-2.0, LICENSE-APACHE, LICENSE-MIT; MPL covers part of the work |
| `packaging` | 26.3 | Apache-2.0 OR BSD-2-Clause | permissive | |
| `pip` | 26.2.1 | MIT | permissive | the installer itself, not an app dependency |
| `playwright` | 1.62.0 | Apache-2.0 (License-Expression) | permissive | your recollection confirmed |
| `pluggy` | 1.6.0 | MIT (+ classifier) | permissive | |
| `pydantic` | 2.13.4 | MIT | permissive | |
| `pydantic_core` | 2.46.4 | MIT | permissive | |
| `pyee` | 13.0.1 | MIT (+ classifier) | permissive | |
| `Pygments` | 2.20.0 | BSD-2-Clause | permissive | |
| `pytest` | 9.1.1 | MIT | permissive | |
| `python-dotenv` | 1.2.2 | BSD-3-Clause | permissive | |
| `PyYAML` | 6.0.3 | MIT (+ classifier) | permissive | |
| `starlette` | 1.6.0 | BSD-3-Clause | permissive | |
| `typing-inspection` | 0.4.3 | MIT | permissive | |
| `typing_extensions` | 4.16.0 | PSF-2.0 | permissive | |
| `uvicorn` | 0.52.1 | BSD-3-Clause | permissive | |
| `watchfiles` | 1.2.0 | MIT (+ classifier) | permissive | |
| `websockets` | 17.0.1 | BSD-3-Clause | permissive | **not** MIT — BSD-3-Clause per metadata |
| `PyYAML`/`websockets`/`httptools` etc. | — | see rows | — | pulled only via `uvicorn[standard]` extras; a fresh `requirements.txt` install does not include them (see docs/DEPENDENCIES.md §2) |

**Classification summary**

- **Permissive (MIT / BSD-2 / BSD-3 / Apache-2.0 / PSF-2.0): 31 packages.**
- **Weak copyleft (MPL-2.0): 2 packages** — `certifi` (whole package) and
  `orjson` (MPL-2.0 component in `MPL-2.0 AND (Apache-2.0 OR MIT)`). MPL-2.0
  is *file-level* copyleft: it matters only for modified MPL-covered files
  that you redistribute.
- **Strong copyleft (GPL / AGPL): none.**
- **Unknown / unstated: none** — every installed distribution declares a
  licence (field, expression, or classifier); `colorama`'s field is empty
  but its shipped LICENSE.txt is the BSD-3-Clause text.

**The redistribution nuance (state it plainly):** every one of these
packages is installed by `pip` on the machine that runs or builds the app.
This repository does **not** vendor, bundle, or redistribute any of their
code — there is no third-party file in the tree (see Part C). Permissive
licences (MIT/BSD/Apache/PSF) condition their obligations on
*redistribution of the licensed work*, so:

- **(i) Publishing this source repository as it stands** → **no obligation
  is triggered** by any of the 33 packages. No notice, no share-alike,
  nothing to include. The licence texts apply to copies of *their* code,
  and none of their code is in the repo.
- **(ii) Shipping a bundled/frozen artifact that contains their code**
  (PyInstaller single binary, Docker image with installed site-packages,
  wheel with vendored deps) → the distribution of each package's code
  triggers its notice duties:
  - **MIT/BSD-2/BSD-3/PSF-2.0:** retain each package's copyright + licence
    notice (a `THIRD_PARTY_NOTICES`/`licenses` folder alongside the artifact
    satisfies this; pip's own `*.dist-info/licenses` can be copied verbatim).
  - **Apache-2.0** (`playwright`, `packaging`): §4 requires a copy of the
    licence, retention of notices/NOTICE files, and a statement of any
    modifications; applies if the artifact embeds their code.
  - **MPL-2.0** (`certifi`, MPL-covered parts of `orjson`): if MPL-covered
    files are modified, those files must be made available under MPL-2.0
    with source; unmodified bundled copies need the licence text and notice
    retained. Practical impact is small for pip-installed unmodified wheels.
  - Share-alike *does* attach in this case (that is what MPL's file-level
    copyleft means), but only to the MPL-covered files you redistribute.

---

## Part B — Data licences (verified from primary sources)

### 1. kaikki.org Spanish extraction + wiktextract

**What kaikki.org states for the extracted data** — the licensing statement
lives on the dictionary index page, not the front/Spanish/rawdata pages
(verified: the front page, the Spanish page, and the raw data page contain
no licence statement at all). Verbatim from
<https://kaikki.org/dictionary/> ("Copyright and license" section, current
as of 2026-08-12; identical wording in the archived 2021 version):

> "This data is extracted from Wiktionary and is updated regularly. The full
> original Wiktionary data can be downloaded from Wikimedia dumps.
> **This data is made available under the same licenses as Wiktionary - both
> CC-BY-SA and GFDL.** See Wiktionary copyright page for more information."

kaikki's statement names **no version** of CC BY-SA and defers to
<https://en.wiktionary.org/wiki/Wiktionary:Copyrights>. It has never claimed
3.0 (checked Wayback snapshots of the front page, dictionary index and raw
data page from 2021, 2022, 2024 and the current site).

**What Wiktionary itself currently states** — the original texts of English
Wiktionary entries are **dual-licensed CC BY-SA 4.0 + GFDL**. Verbatim from
<https://en.wiktionary.org/wiki/Wiktionary:Copyrights> (current):

> "The original texts of Wiktionary entries are dual-licensed to the public
> under both the **Creative Commons Attribution-ShareAlike 4.0 International
> License** (CC-BY-SA) and the **GNU Free Documentation License** (GFDL)."

and from the Wikimedia Foundation Terms of Use §7
(<https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use>):

> "When you submit text to which you hold the copyright, you agree to
> license it under: Creative Commons Attribution-ShareAlike 4.0
> International License ('CC BY-SA 4.0'), and GNU Free Documentation
> License ('GFDL') (unversioned, with no invariant sections, front-cover
> texts, or back-cover texts). **Reusers may comply with either license or
> both.**"

Wikimedia moved text licensing from CC BY-SA 3.0 to **4.0 effective
2023-06-01** (Wikimedia Foundation announcement; see
<https://diff.wikimedia.org/2023/06/29/stepping-into-the-future-wikimedia-projects-transition-to-creative-commons-4-0-license/>
and <https://creativecommons.org/2023/06/29/wikipedia-moves-to-cc-4-0-licenses/>).
So: **the current licence is CC BY-SA 4.0 + GFDL** (the README's earlier
"CC BY-SA 3.0" claim was stale and has been corrected). kaikki's deferral
("same licenses as Wiktionary") therefore resolves to 4.0 today. (Content contributed before 2023-06-01 remains
available under 3.0 per its original grant; the ToU §8 additionally says
modifications are licensed "under CC BY-SA 4.0 or later".) Practical note:
reusers may comply with either licence; CC BY-SA is the workable path —
GFDL carries transparent-copy and cover-text machinery that is impractical
for a database/app.

**wiktextract tool licence** — **MIT**. Verbatim from the README
(<https://github.com/tatuylonen/wiktextract>):

> "Copyright (c) 2018-2020 Tatu Ylonen. This package is free for both
> commercial and non-commercial use. It is licensed under the MIT license.
> See the file LICENSE for details. (Certain files have different open
> source licenses)"

The LICENSE file adds: "Certain files under tests/ are under Wiktionary
license (CC-BY-SA or GFDL at your choice)." The tool's code is MIT; the
*data* it extracts carries Wiktionary's licence (per kaikki's statement
above). kaikki also requests a citation for academic use: Tatu Ylonen,
"Wiktextract: Wiktionary as Machine-Readable Structured Data", LREC 2022,
pp. 1317–1325, <http://www.lrec-conf.org/proceedings/lrec2022/pdf/2022.lrec-1.140.pdf>.

### 2. Frequency data

The frequency source was swapped on 2026-08-12. Both halves are documented
here: the superseded SUBTLEX-ESP record (kept because the history explains
*why* the swap happened) and the current FrequencyWords source.

#### 2a. SUBTLEX-ESP — **superseded 2026-08-12**

SUBTLEX-ESP (Cuetos, Glez-Nosti, Barbón & Brysbaert, 2011) was the
frequency source until the 2026-08-12 swap. Its canonical distribution page
(Center for Reading Research, Ghent University — `http://crr.ugent.be/archives/679`,
now 404) carried this notice, verbatim and identical in the 2013-09-27 and
2018-03-25 Wayback snapshots:

> "This work is licensed under a **Creative Commons
> Attribution-NonCommercial-NoDerivs 3.0 Unported License**."

That is **CC BY-NC-ND 3.0**, and the ND element was the blocker: the
pipeline merged SUBTLEX per-million values into `data/morph.sqlite`
(a transformed/derived work), so distributing the DB was a distribution of
an ND-licensed derivative and the NC element barred commercial use — see
`docs/FREQUENCY_IMPACT.md` for the full impact study. The repo's
`SUBTLEX-ESP.xlsx` was proven to be the genuine file (SHA-256
`6e7b099ca87efa28c16bb1aafd51fc9e383182210f1bca621b7fd9b137657acb`, matching
the archived CRR distribution). The file still sits untracked at the repo
root (nothing reads it anymore) and may be deleted at any time.

Academic citation (for the record): Cuetos, F., Glez-Nosti, M., Barbón, A.,
& Brysbaert, M. (2011). SUBTLEX-ESP: Spanish word frequencies based on film
subtitles. *Psicológica*, 32(2), 133–143.

#### 2b. FrequencyWords — current source

**Source:** <https://github.com/hermitdave/FrequencyWords>, Spanish list
`content/2018/es/es_full.txt` — 14,547,688 bytes, 1,202,520 `word␣count`
lines, raw OpenSubtitles-derived counts (the repo README points the 2018
lists at <http://opus.nlpl.eu/OpenSubtitles2018.php>).

**Licence, verified from the repository itself** (read 2026-08-12):

- The root `LICENSE` file is the MIT License, © 2016 Hermit Dave — it
  covers the *code* (the list generator).
- The README's License section states the split explicitly, verbatim:
  "MIT License for code.<br>CC-by-sa-4.0 for content."

So the frequency **data** is **CC BY-SA 4.0** per the repository's own
attribution. The pipeline normalises the raw counts to per-million
(`count / corpus_total × 1,000,000`, corpus total 423,290,924 tokens),
which is a transformation fully permitted by CC BY-SA 4.0 (share-alike,
with attribution). Both datasets feeding the build — Wiktionary content and
FrequencyWords frequencies — are now CC BY-SA 4.0, so the whole built
artifact carries a single uniform licence (see Part C).

---

## Part C — What this repository does and does not redistribute

Verified against the git tree (`git ls-files`), `.gitignore`, and the
working files:

- **The two source datasets are NOT in the repository.** `kaikki.org-dictionary-Spanish.jsonl` (979 MB) and `es_full.txt` (14.5 MB) sit untracked at the repo root; `.gitignore` covers `*.jsonl`, `es_full.txt`, `data/`, `*.sqlite`. (The superseded `SUBTLEX-ESP.xlsx` also sits untracked, now unused.) Neither appears in `git ls-files`.
- **`data/morph.sqlite` is NOT in the repository.** `data/` is fully gitignored (the 295 MB DB, the ~557 MB of JSONL intermediates, `reject_hacer.txt` are all untracked).
- **No third-party code is vendored anywhere.** `app/static/` contains exactly three hand-written files (`index.html` 1.5 KB, `app.js` 26.7 KB, `styles.css` 12 KB). Grep for `minified`, `jquery`, `bootstrap`, `react`, `vue`, `angular`, `cdn.`, `unpkg`, `googleapis`, `@import`, `url(` → **zero hits**. No bundled library, no minified vendor file, no webfont, no CDN reference. (The app's only network calls are two same-origin `fetch("/api/...")` calls.) There is no `LICENSE`/`NOTICE`/`COPYING` file anywhere in the tree.
- **`app/fixtures/sample.json` (261 KB) IS tracked and contains derived Wiktionary glosses — but no FrequencyWords data.** Verified mechanically: (V1) all 1,259 `freq` values are round to one decimal (144 distinct, range 0.1–160.0, heavy repeats, `hacer` = `hizo` = 160.0); cross-checked against `data/morph.sqlite`'s 1.2 M `form.freq` rows for the same surface forms → **0 exact matches** (re-verified 2026-08-12 against the FrequencyWords-built DB; the 2 nearest, `hechizos` 3.5 vs 3.47 and `mentí` 13.6 vs 13.67, are not roundings of the real per-million values). The fixture frequencies are hand-invented demo values. (V2) Of its 46 glosses, checked word-by-word against the raw kaikki JSONL: 1 verbatim (`desaprobar` → "to disapprove"), 16 abridged (fixture gloss is a shortened/condensed form of a kaikki gloss, e.g. `mentir` "to lie" ← "to lie (say something untrue)", `hacer` "to do, to make" ← "to do, perform, execute, carry out" + "to make…"), 6 lightly reworded/reordered (`hacedero` "feasible, doable" ← "doable, feasible"), and 23 with no direct match — of which ~11 are the project's own synthetic/fictional entries explicitly marked "(synthetic)"/"(rare)"/"fictional" and the rest are paraphrases of Wiktionary senses (e.g. `desmentir` "to deny" ← "to refute, discredit"). So the fixture is a small hand-curated sample whose real-word glosses are derived from (mostly abbreviated) Wiktionary gloss text; it is the one committed artifact that carries third-party content today.
- **`data/morph.sqlite` IS a derivative work of both datasets — both CC BY-SA 4.0.** `pipeline/build.py` merges, per lemma and per form: Wiktionary content extracted from the kaikki JSONL (word forms, glosses, etymological/derivational relations, paradigms) and FrequencyWords per-million frequencies (`pipeline/frequency.py` reads `es_full.txt` and normalises the raw counts; build.py attaches `freq` to every lemma/form row). It is not currently distributed; if it were, a single CC BY-SA 4.0 licence covers the whole artifact (see scenario 2).

### The three scenarios

**1. Today — publishing this source repository (no data files, no DB):**

- **Code:** no attribution obligations for the pip dependencies (Part A).
  The repo's own code is licensed **MIT (© 2026 AndroEhab)** — see
  `LICENSE`; the embedded dictionary content stays **CC BY-SA 4.0** — see
  `LICENSE-DATA.md`.
- **Data:** the tracked `app/fixtures/sample.json` carries glosses derived
  from Wiktionary gloss text (abridged/reworded, one verbatim — see Part C),
  so **CC BY-SA attribution is due today**: credit Wiktionary (CC BY-SA 4.0
  + GFDL) wherever the fixture data is presented (README + app footer), link
  the licence, and note modification. **No frequency-source exposure
  today**: the fixture contains zero real FrequencyWords values (verified),
  and the NC-ND-licensed SUBTLEX xlsx — now unused — is not distributed and
  no longer feeds the build. Nothing CC BY-NC-ND attaches to this
  repository or its output anymore.
- **Concretely:** add a short "Data sources" notice (app footer + README)
  with the two attribution strings below.

**2. If the built `data/morph.sqlite` were distributed** (release asset,
Docker image, bundled wheel):

- The DB is a derivative of Wiktionary content → **CC BY-SA 4.0 share-alike
  attaches**: the DB (or a DB-licensing statement) must be released under
  CC BY-SA 4.0 (or later), with attribution to Wiktionary (and kaikki.org
  for the extraction), a link to the licence, and a statement of
  modification. GFDL remains an alternative but is impractical for a
  database.
- The DB also embeds FrequencyWords values → **CC BY-SA 4.0, same licence as
  the Wiktionary content**: the merged DB is released under CC BY-SA 4.0
  (or later) with attribution to Wiktionary/kaikki.org *and* to
  FrequencyWords (OpenSubtitles-derived, CC BY-SA 4.0), a link to the
  licence, and a statement of modification. **No NC/ND blocker remains** —
  commercial distribution of the DB is now within the licence grant. (This
  replaces the pre-2026-08-12 finding, where SUBTLEX-ESP's CC BY-NC-ND 3.0
  made distribution materially problematic.)
- Practical note: the ~993 MB raw datasets (kaikki JSONL, `es_full.txt`)
  should still stay out of any distribution — not because of licence
  restrictions (both are CC BY-SA 4.0) but because they are large and
  regenerable from their sources.

**3. If the app were hosted publicly** (users query Wiktionary-derived
content over the web):

- Serving CC BY-SA content to the public is a "publication" of a derivative
  work: provide **attribution** (credit Wiktionary + kaikki.org, link to the
  licence, note that content was modified/extracted), and the served
  database remains a CC BY-SA derivative for any further distribution.
  Attribution must be *conspicuous* — an app footer/settings/"About" page
  is the natural place; a README alone is not enough for end users.
- With FrequencyWords the frequency data carries **no NC/ND restrictions**:
  the served, merged database is a CC BY-SA 4.0 derivative for commercial
  and non-commercial hosting alike, provided attribution is conspicuous
  (footer, as above) and share-alike applies to any further distribution.
  (Pre-2026-08-12, SUBTLEX-ESP's NC element barred commercial use and its
  ND element barred the transformed/merged presentation — see §2a.)

**Attribution strings (copy-paste ready):**

- Wiktionary/kaikki:
  "Word data derived from [English Wiktionary](https://en.wiktionary.org)
  via the [kaikki.org Spanish extraction](https://kaikki.org/dictionary/Spanish/),
  licensed under the [Creative Commons Attribution-ShareAlike 4.0
  International](https://creativecommons.org/licenses/by-sa/4.0/) and the
  [GNU Free Documentation License](https://www.gnu.org/licenses/fdl-1.3.html)
  (dual-licensed; text modified/extracted). Wiktionary: Tatu Ylonen,
  'Wiktextract: Wiktionary as Machine-Readable Structured Data', LREC 2022."
- FrequencyWords:
  "Frequency data from the [FrequencyWords](https://github.com/hermitdave/FrequencyWords)
  Spanish frequency list (`content/2018/es/es_full.txt`,
  OpenSubtitles-derived, © Hermit Dave and contributors), licensed under the
  [Creative Commons Attribution-ShareAlike 4.0
  International](https://creativecommons.org/licenses/by-sa/4.0/) License
  (per the repository: 'MIT License for code. CC-by-sa-4.0 for content.')."

---

## Repository licensing status

The project code is licensed under the **MIT License** (© 2026 AndroEhab) —
see the `LICENSE` file at the repo root. The **code licence and the content
licence are separate questions, deliberately stated in two files**: the code
can be (and is) licensed however the owner chooses, while the linguistic
content **cannot be relicensed** — it derives from CC BY-SA 4.0 sources and
remains CC BY-SA 4.0 (and GFDL for the Wiktionary-derived text) with its own
attribution/share-alike obligations regardless of what the code licence
says. The content licence and the attribution strings live in
`LICENSE-DATA.md` at the repo root; the MIT text stays unmodified in
`LICENSE` so that tooling and GitHub's licence detection can recognise it.

If verbatim or near-verbatim Wiktionary content stays in the repo (the
fixture's abridged glosses qualify), the **code licence and the content
licence are separate questions**: the code can be licensed however the
owner chooses, while the embedded dictionary content remains CC BY-SA 4.0
(and GFDL) and carries its own attribution/share-alike obligations
regardless of what the code licence says.
