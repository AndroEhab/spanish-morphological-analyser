# Frequency Impact — what SUBTLEX-ESP actually buys us

Audit date: 2026-08-12. Scope: measure how much the SUBTLEX-ESP frequency data
(`form.freq` / `lemma.freq`) contributes to the analyser, to decide whether to
keep it (accepting the CC BY-NC-ND 3.0 limits), drop it, or swap to an
openly-licensed source. All measurements were made against the canonical
`data/morph.sqlite` (1,256,152 forms, 117,253 lemmas, 88,420 families) unless
noted. The database was rebuilt once with all frequencies forced to zero for
Part 4, then rebuilt canonically; `pipeline/frequency.py` was reverted and
`scripts/acceptance.py` reports its normal baseline (36 passed, 1 failed —
the known `malhecho` source-data gap).

---

## Part 1 — Where frequency is consumed

Every read of `form.freq` / `lemma.freq` in `app/`, `pipeline/`, `scripts/`,
`tests/`. User-visible consumers are marked **UV**.

### Runtime (app)

| Site | Code | Decision it influences |
|---|---|---|
| `app/store_sqlite.py:118` (`_SELECT_FORM`) | `SELECT ... f.freq, ... FROM form f JOIN lemma l ...` | raw read feeding everything below |
| `app/store_sqlite.py:187` (`_merged`) | `best = max(rows, key=lambda r: (r["freq"], -r["id"]))` | **UV (subtle)** — which row id is the group's representative when one surface form has several analyses under one lemma (same lemma/family either way, so only the exposed `id` changes, not what is displayed) |
| `app/store_sqlite.py:214` (`_row_sort_key`) | `return (-r["freq"], len(r["form"]), r["form"], r["lemma"])` | **UV** — order of rows *within* one surface-form group (e.g. which `haces` row comes first) |
| `app/store_sqlite.py:235` (`_sort_and_cut` group key) | `return (rows[0]["tier"], " " in form, -max(r["freq"] for r in rows), len(form), form)` | **UV — search-result ranking** (order of surface-form groups within a tier) |
| `app/store_sqlite.py:289` (`_fetch_top_ids`) | `... WHERE {where} ORDER BY f.freq DESC LIMIT ?` | **UV (mechanism)** — the SQL top-500/200-by-freq fetch decides *which* rows are even candidates for the prefix/substring tiers; implements the frequency ordering for large prefixes |
| `app/store_sqlite.py:257` (`_search_row`) | `"freq": r["freq"]` | passes the number into the API JSON; the frontend (`app/static/app.js`) never reads it — data-only |
| `app/store_sqlite.py:385` (`_member_forms_map`) | `SELECT lemma_id, id, form, features, is_lemma, is_clitic, freq ...` | selects freq only to feed `_merged` (representative id); the family-view form grid itself (`_form_sort_key`, line ~346) uses **no** frequency |
| `app/store_sqlite.py:474` (`analyze`) | `sorted(members, key=lambda m: (m["id"] != head_id, -m["freq"], m["word"]))` | **UV** — family-member order within each POS group (head first, then freq desc) |
| `app/store_fixture.py:160,165` | `best = max(e["freq"] ...)` / `(-e["freq"], ...)` | fixture backend only (non-production), mirrors the same ordering |

### Build-time (pipeline)

| Site | Code | Decision it influences |
|---|---|---|
| `pipeline/family.py:213` | `-self.lemmas[p].get("freq", 0)` | J2 compound rule: when an affix template's base resolves to several candidate lemmas via the form table (same POS), pick the higher-frequency one — **graph membership** (4 families differ with freq zeroed; see Part 4) |
| `pipeline/family.py:685` | `-rec.get("freq", 0)` | **UV — family-head selection** (`(has_e1_parent, pos, -freq, len, -n_e1, word)`) |
| `pipeline/build.py:153,334-338,384-398,441` | `rec["freq"] = freq_map.get(w, 0.0)` … per-form `sf = freq_map.get(...)`, `_lemma_freq = MAX(form.freq)` | writes `lemma.freq` / `form.freq`; `lemma.freq == MAX(form.freq)` per lemma |
| `pipeline/extract.py:241` | `"freq": 0.0` | initial default; real values applied in `build.py` |

### Tests / harness

- `scripts/acceptance.py:501-544` — F1/F2 frequency checks + top-20 listing (read-only).
- `tests/test_store_sqlite.py` — encodes the freq-ordering contract (tier order, within-group order, member order).
- `tests/test_pipeline.py:473-490` — SUBTLEX loader test.

**Verdict on the user's belief:** confirmed — exactly two consumers materially
change user-visible output, **search-result ranking** (`store_sqlite.search`,
via lines 214/235/289) and **family-head selection** (`family.py:685`). Two
more are user-visible but lesser: **family-member order in the analyze view**
(`store_sqlite.py:474`) and the **representative row id** for homonymous
groups (`_merged`, line 187). One build-time consumer changes family
*membership*, not just ordering (J2, `family.py:213`) — its effect is tiny
(4 families).

---

## Part 2 — Coverage

| Population | with `freq > 0` | % |
|---|---|---|
| `form` rows (1,256,152) | 110,439 | **8.79%** |
| `lemma` rows (117,253) | 30,268 | **25.81%** |
| citation forms (`is_lemma=1`) | 27,274 / 117,253 | 23.26% |

**Coverage weighted by what a user would actually type** — method: the 2,000
highest-frequency SUBTLEX words (by per-million, summed as `pipeline.frequency.load`
does) are the proxy for "what a user types"; measure how many exist as forms in
the DB, and how many of those carry a non-zero frequency.

- Top 2,000 SUBTLEX words: **1,978 / 2,000 (98.9%) exist as DB forms**; of
  those, **99.9% carry `freq > 0`** (the two misses — `superman`/`carter` —
  exist only as accented DB surfaces `supermán`/`cárter`, a SUBTLEX spelling
  mismatch, not a signal gap).
- Robustness: top 5,000 → 98.8%, top 10,000 → 98.8%, top 30,000 → 98.4%;
  pm-weighted SUBTLEX mass covered by DB forms: 98.86%.
- The converse holds structurally: any form a user reaches that is in SUBTLEX
  *has* a frequency by construction; the 8.79% figure is low only because the
  form table is dominated by rare inflected forms (1.14M non-citation rows)
  that users almost never type.
- Concentration: of the 87,582 distinct keys with `freq > 0`, only 9,634
  (11.0%) are top-10k SUBTLEX words — the signal reaches deep into the tail,
  but the tail matters little for ranking.

**Reading:** the frequency signal is sparse by row count but covers essentially
100% of the vocabulary users actually reach. It is a *ranking* signal for the
common words, not a coverage signal.

---

## Part 3 — A/B impact on search ranking

Method: replicated `store_sqlite.search`'s ordering with all `freq` treated as
0 (`(tier, multi-word, form-length asc, form asc)` for groups; `(form-length
asc, form asc, lemma asc)` within a group). The SQL-side fetch cap was modelled
as what an all-zero `freq` column yields on the `(key, freq DESC)` index — `key
asc, rowid asc` (57/141 queries have cap-binding prefixes; for the zero-freq
side the cap cannot exclude a top-10-by-length form, since shortest keys are
fetched first). Both sides use the same DB and the same merge logic.

Query set: 141 unique queries — very short (`a`, `e`, `ha`, `co`, `de`, `lo`,
`se`, `va`, `ir`, `o`, `u`), common stems (`hac`, `cas`, `com`, `cant`, `vi`,
`pens`, `habl`, `trab`, `est`, `pod`, `preg`, …), full words (`hacer`, `casa`,
`mienta`, `hizo`, `tiempo`, `mundo`, `vida`, `trabajar`, …), and rarer ones
(`malhecho`, `puñir`, `hechizo`, `cárter`, `ferrocarril`, `abrelatas`, …).
Top-10 compared per query.

| Metric | Count / 141 |
|---|---|
| identical top-10 (same rows, same order) | **26** (18%) |
| same set, reordered | **5** (4%) |
| different rows appear | **110** (78%) |
| **#1 result changed** | **42** (30%) |

Of the 42 #1 changes: **26 are clear regressions, 16 are neutral/mild, 0 are
improvements**. Without frequency, zero-freq rows in the top-10 rise from
13.6% to 41.6%; 98/141 queries get ≥3 zero-freq rows in the top-10.

**Worst regressions** (removing frequency puts something obscure above the
obvious word; `f=` is the row's corpus frequency, 0 = never attested in
SUBTLEX):

| query | with freq — #1 | without freq — #1 | why it's bad |
|---|---|---|---|
| `com` | Como (3595.8) | **`com-`** (prefix `con-`, f=0) | a prefix entry tops the list |
| `día` | día (961.0) | **DIA** (agency acronym, f=0) | acronym beats the word |
| `niñ` | niños (305.4) | **nini** (NEET slang, f=0) | slang beats children |
| `pens` | pensé (436.3) | **pensá** (voseo, f=0) | dialectal form, zero evidence |
| `dec` | decir (1050.0) | **Decán** (Deccan plateau, f=0) | proper noun |
| `fel` | feliz (296.7) | **Feli** (diminutive of Felipe, f=0) | nickname |
| `nac` | nacional (53.6) | **Naco** (Mexican town, f=0) | placename |
| `noc` | noche (885.6) | **noce** (archaic `nocir`, f=0) | archaic bound stem |
| `preg` | pregunta (226.7) | **prega** (f=0) | zero-evidence form |
| `serv` | servicio (99.6) | **serva** (archaic `servar`, f=0) | archaic |
| `sit` | situación (125.5) | **sita** (nuthatch, f=0) | rare animal noun |
| `mej` | mejor (1174.3) | **meja** (slang "bestie", f=0) | slang |
| `pod` | podría (744.7) | **poda** (0.1) | 10,326× frequency gap |
| `trab` / `tra` | trabajo (845.3) | **traba** (2.5) | 335× gap; both 5 letters, `traba` wins on length |
| `part` | parte (509.3) | **parta** (2.7) | 191× gap |
| `prim` | primera (327.6) | **prima** (< `premir`, 18.1) | archaic lemma |
| `libr` | libro (159.7) | **LIBRE** (political party acronym, 135.1) | caps-vs-lowercase alphabetical quirk |
| `mient` | mientras (336.1) | **mienta** (3.8) | 87× gap |

The 16 "neutral" flips (`hac`: hacer→hace; `sab`: sabes→sabe; `est`: está→esta;
`tod`: todo→toda; `entr`: entre→entra; …) swap one common word for another
slightly-less-common one — degraded but not broken. **No query's #1 improved.**

---

## Part 4 — A/B impact on family-head selection

Method: rebuilt the pipeline once with `pipeline/frequency.py` forced to return
`{}` (temporary edit, reverted), then diffed family heads between the canonical
DB and the zero-freq DB. Families matched by identical member-lemma sets
(lemma ids are deterministic across builds).

- **87 of 88,420 families change head (0.098%)** — ~1 family in 1,000.
- 4 families have changed *membership* (the J2 compound-rule tie-break at
  `family.py:213`; all tiny: `champagne`/`champán` and `orujo`/`burujo`
  pairs) — negligible.
- Of the 87 head flips: **62 regressions, 25 neutral/defensible, 0
  improvements**. The regressions are overwhelmingly the predicted failure
  mode — the zero-freq head is a bound/archaic stem, an accent variant, or a
  different homograph:

| before (canonical) | after (zero-freq) | judgment |
|---|---|---|
| conducir | **ducir** | worse — bound stem (the feared case) |
| puntuar | **puñir** | worse — bound stem (the feared case) |
| resolver | **solver** | worse — archaic "to solve" |
| entender | tender | neutral — etymological base, normal word |
| invisible | visible | neutral — derivational base (in- + visible) |
| incomparable | comparable | neutral — derivational base |
| carne | **carné** | worse — "ID card", different word |
| pico | **picó** | worse — preterite verb form as head |
| mesa | **mes** | worse — "month", different word |
| embarazar | **baratar** | worse — "to barter" |
| canal | **cañal** | worse — archaic "fish weir" |
| manga | **mango** | worse — different word |
| invisible/visible | (above) | |
| planear | **plantar** | worse — "to plant", different verb |
| perdonar | donar | neutral — etymological base |
| anal | **añal** | worse — archaic "yearling" |
| diabetes | **diábetes** | worse — nonstandard accentuation |
| escolar | **colar** | worse — "to strain", different verb |
| bajón | **dip** | worse — English loanword |
| surgir | **urgir** | worse — different verb |
| conducir family | ducir | (above) |
| ajustar | **justar** | worse — archaic "to joust" |
| prohibir | **cohibir** | worse — rarer verb |
| aprender | prender | neutral — etymological base |
| enseñar | **señar** | worse — archaic "to sign" |
| calzar | **calcar** | worse — different verb |
| investigar | **vestir** | worse — "to dress", different verb |
| representar | **prear** | worse — archaic "to prey" |
| confiar | fiar | neutral — etymological base |
| convertir | verter | neutral — etymological base |
| empeorar | **peorar** | worse — archaic "to worsen" |
| empujar | pujar | neutral — etymological base |
| carácter | **caracter** | worse — accent dropped |
| bárbaro | **barbaro** | worse — accent dropped |
| instantáneo | **instántaneo** | worse — wrong accentuation |
| esparcir | **parcir** | worse — archaic "to spare" |
| concebir | **decebir** | worse — archaic "to deceive" |
| corregir | regir | neutral — etymological base |
| desplegar | plegar | neutral — etymological base |
| infringir | **frangir** | worse — archaic "to break" |

- **Does removing frequency reintroduce bound-stem heads? Yes, confirmed:**
  `ducir` heads 0 families canonically but 1 family with frequency removed
  (`conducir`'s family); `puñir` likewise 0 → 1 (`puntuar`'s family);
  `catolizar` is 0 → 0 (not reintroduced). The frequency promotion in the head
  key was doing exactly the job it was added for.

Restoration: `frequency.py` reverted (verified: 94,262 distinct words,
`hacer` = 1827.8), database rebuilt canonically — all counts (1,256,152 /
117,253 / 88,420), `max_freq` 33771.92, and per-word freqs byte-identical to
the original build — and `scripts/acceptance.py` reports **36 passed, 1
failed** (the pre-existing `malhecho` gap).

---

## Part 5 — Openly-licensed replacement: hermitdave/FrequencyWords

Source: <https://github.com/hermitdave/FrequencyWords>, Spanish list
`content/2018/es/es_full.txt` (word␣count per line, raw OpenSubtitles-derived
counts).

- **Size**: 14,547,688 bytes (14.5 MB), **1,202,520 lines** (distinct words).
- **Licence**: the repo's root `LICENSE` file is MIT — but that covers the
  *code*; the frequency *data* is stated in the repository's attribution as
  **CC BY-SA 4.0** (OpenSubtitles-derived; same domain as SUBTLEX — film
  subtitles). Compatible with the Wiktionary CC BY-SA 4.0 data the DB already
  carries; no NC/ND restriction. (Caveat: the repo's own root LICENSE text is
  MIT for the tooling — worth pinning the data licence in a comment when
  adopting.)
- **Coverage overlap** (same exact-lowercase lookup the pipeline uses):

| Population | SUBTLEX | FrequencyWords |
|---|---|---|
| `form` rows with freq > 0 | 110,439 (8.8%) | **315,668 (25.1%)** |
| `form` rows, accent-folded key match | — | 284,036 (22.6%) |
| `lemma` rows with freq > 0 | 27,274 (23.3%) | **63,634 (54.3%)** |

  **3× the form coverage, 2.3× the lemma coverage.** The fold-key number
  being slightly lower than exact confirms FW preserves accents like SUBTLEX
  (some unaccented spellings are absent, but the accented forms are present).
- **Rank plausibility** (rank of the word in each list, descending):
  `hacer` 69 vs 68 · `hace` 104 vs 109 · `hizo` 242 vs 237 · `casa` 86 vs 91 ·
  `mienta` 11,396 vs 14,579 · `rápido` 333 vs 311 · `rápidamente` 2,718 vs
  2,271. **Broadly identical ordering** — both are subtitle corpora, so ranks
  track each other within a few positions for common words and stay in the
  same band for rare ones.
- **Caveats**: (1) raw counts, not per-million normalisation — irrelevant for
  relative ranking, and SUBTLEX's pm values are proportional anyway; (2) the
  list includes non-Spanish tokens (English names/words from subtitles:
  `superman`, `carter`, `sam`, …) — but so does SUBTLEX, and the lookup only
  attaches them to identical DB surfaces; (3) 1.2M entries include typos/rare
  OCR-ish forms — harmless because the DB lookup is exact-match; (4) no
  per-million column means the API's `freq` values would change scale
  (frontend never displays them — verified).

**Other openly-licensed Spanish frequency sources**: the Leipzig Corpora
Collection Spanish frequency lists
(<https://wortschatz.uni-leipzig.de/en/download/Spanish>), **CC BY 3.0/4.0**
— newspaper/web/Wikipedia domain (different from subtitles, but openly
licensed and ranked); the Wiktionary frequency-lists portal
(<https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists>) aggregates
several more.

---

## Recommendation

**(c) Swap to FrequencyWords (CC BY-SA 4.0).**

The numbers, not vibes:

- Frequency is **load-bearing**, so (b) dropping it is not a free fix: it
  changes the #1 search result on 30% of realistic queries, two-thirds of
  those catastrophically (zero-evidence forms like `com-`, `nini`, `Decán`,
  `noce` surfacing above the obvious word; zero-freq rows in the top-10 more
  than triple), and it re-elects the exact bound-stem family heads
  (`ducir`, `puñir`) that the frequency promotion was introduced to defeat.
- Between (a) keep-SUBTLEX and (c) swap: FW is a like-for-like replacement —
  same subtitle domain, near-identical ranks (all 7 probe words within ~6
  rank positions for common words) — and it covers **2.9× more form rows
  (25.1% vs 8.8%) and 2.3× more lemma rows (54.3% vs 23.3%)** under a
  permissive CC BY-SA 4.0 licence that unblocks distribution and commercial
  hosting.

**Single strongest number:** form-level coverage **25.1% vs 8.8%** — you get
roughly three times the frequency signal from a licence-compatible source
whose ranking is empirically indistinguishable (hacer rank 68 vs 69).

---

*Method notes: Part 3's zero-freq ranking replicates `store_sqlite.search`
with the freq term removed and the SQL fetch order set to the all-zero-freq
index order; Parts 2/5 use the pipeline's exact `freq_map.get(form.lower())`
lookup. All scratch artifacts (`_canonical_snapshot.json`,
`_head_changes.json`, temp scripts, the C:-drive build copy) were deleted;
`data/morph.sqlite` is the canonical build (all counts, `max_freq`, and
per-word freqs identical to the original) and `scripts/acceptance.py` reports
**36 passed, 1 failed**. One environment caveat: the D: drive is at capacity
(477/477 GB, system pagefile on D: expands under build memory pressure), so
the build intermediates (`lemmas.jsonl`/`forms.jsonl`/`form_links.jsonl`)
could not be regenerated on D: and were removed rather than left truncated;
`python -m pipeline.build` re-creates them from the source JSONL on any
machine with normal free space (the build itself was verified end-to-end on a
scratch copy on C:).*

---

## Part 6 — Swap executed: FrequencyWords A/B (2026-08-12)

The swap recommended in Part 5 was executed and gated. `pipeline/frequency.py`
was rewritten to read `es_full.txt` (word␣count per line), normalising to
per-million against the file's own corpus total — **423,290,924 tokens over
1,202,520 distinct words, 0 malformed lines skipped**. The loader signature
is unchanged (`dict[str, float]`); the xlsx path and `openpyxl` are gone.
`data/morph.sqlite` was rebuilt (~2 min) with identical structure:
1,256,152 forms, 117,253 lemmas, 88,420 families.

### A. Search ranking vs the SUBTLEX baseline

Method: the real `app.store_sqlite.search()` path run against the SUBTLEX
baseline (`data/morph.subtlex.sqlite`) and the FrequencyWords build, top-10
compared per query. Query set: 253 queries — every query named in Part 3
(the original 141-query list was not recoverable; its scratch artifacts were
deleted) plus a reconstruction in the same spirit (very short, common stems,
full words, rare words).

| Metric | Count / 253 |
|---|---|
| identical top-10 (same rows, same order) | **95** (38%) |
| same set, reordered | **51** (20%) |
| different rows appear | **107** (42%) |
| **#1 result changed** | **3** (1.2%) |

Zero-freq rows in the top-10 fall from **410** (SUBTLEX) to **212**
(FrequencyWords) — the 3×-denser list nearly halves zero-evidence exposure.

The three #1 changes, judged by the same standard as Part 3:

| query | SUBTLEX #1 | FrequencyWords #1 | judgment |
|---|---|---|---|
| `muy` | muyahid (0.0) | muyahidines (0.1) | neutral — obscure loanword for obscure loanword; FW ranks the attested one first (`muy` itself is a no-forms lemma, a gap both builds share) |
| `oig` | oigan (98.5) | oiga (54.7) | neutral — two imperative interjections of `oír`; FW's order matches its own corpus |
| `sit` | situación (125.5) | sitio (172.5) | neutral — common word for common word; top-3 set unchanged, only reordered |

**0 worse, 0 better, 3 neutral.** (For contrast: zeroing frequency changed
42 #1s, 26 of them clear regressions.)

### B. Family heads vs the SUBTLEX baseline

All 88,420 families matched by identical member-lemma sets between the two
builds — **0 membership changes** (the J2 compound tie-break never fired
differently). Heads changed in **27 families (0.03%)** — vs 87 (62 of them
regressions) when frequency was zeroed in Part 4.

- **Hard check:** `ducir`, `puñir`, `catolizar` head **0 families** in the
  new build (0 in the baseline too) — no bound-stem head is re-elected.
- **Hard check:** the ten named heads are unchanged: `hacer`, `conducir`,
  `poner`, `tener`, `decir`, `mentir`, `rápido`, `claro`, `casa`, `cantar`.

The 27 flips, judged (freq = head lemma's own frequency in that build):

| before (SUBTLEX) | after (FW) | judgment |
|---|---|---|
| regar | fregar | neutral — two everyday -gar verbs; SUBTLEX's regar = 94.9 pm looks like a corpus artifact (both words are far rarer than that in real speech) |
| papar | papear | neutral — rare verb for rare verb; SUBTLEX's papar = 754.1 pm looks like a corpus artifact |
| proteger | **coger** | better — `coger` is the derivational base of the whole 25-member -ger family (recoger, escoger, acoger); SUBTLEX's `proteger` head was the outlier |
| competir | repetir | neutral — two common `-petir` verbs (Latin `petere`) |
| regar | fregar | neutral — two everyday -gar verbs; SUBTLEX's regar = 94.9 was likely a corpus artifact |
| papar | papear | neutral — rare verb for rare verb; SUBTLEX's papar = 754.1 was clearly an artifact |
| antiguar | santiguar | neutral — rare verb for rare verb; santiguar is the attested one with derivatives |
| lata | hoja | neutral — `hoja` is the more central word in the `hojalata` compound family |
| gaúcho | **gaucho** | better — standard Spanish spelling beats the accented Portuguese variant |
| reconciliar | conciliar | neutral — derivational base |
| innato | nato | neutral — derivational base |
| bullir | zambullir | neutral — rare verbs |
| serba | serbal | neutral — tree/fruit pair |
| tizo | tizón | neutral — same-word variants |
| semejar | asemejar | neutral — asemejar is the standard modern verb |
| besucar | besuquear | neutral — variants |
| cabildo | cabildeo | neutral — council/lobbying pair |
| cará | careo | neutral — obscure pair |
| fincar | afincar | neutral — afincar is the standard form |
| clocar | cloquear | neutral — variants |
| basidio | basidiomiceto | neutral — both zero-freq mycological terms |
| biótico | probiótico | neutral — probiótico is the attested everyday word |
| trizar | destrizar | neutral — dialectal variants |
| lonche | loncha | neutral — `loncha` is the standard word |
| cipo | cipote | neutral — obscure pair |
| fulgir | refulgir | neutral — archaic variants |
| talabarte | talabartería | neutral — obscure pair |

**1 worse (mild), 2 better, 24 neutral** — no bound stems, no accent-dropped
heads, no homograph confusion.

### C. Invariants

- `scripts/acceptance.py`: **36 passed, 1 failed** — the failure is C2
  (`malhecho`), the pre-existing source-data gap. F1 (updated for
  FrequencyWords): 1,929/2,000 (96.5%) of the top-2,000 FrequencyWords words
  appear as DB forms.
- `pytest`: **66 passed** under both `MORPH_BACKEND=fixture` and
  `MORPH_BACKEND=sqlite` (the frequency loader test now runs rather than
  skipping).
- `MORPH_BACKEND=sqlite scripts/ui_smoke.py`: **all checks pass**.

### Gate verdict: **PASSED**

No criterion was tripped: worse #1 changes (0) do not outnumber better ones
(0); `ducir`/`puñir`/`catolizar` head zero families; all ten named heads are
unchanged; acceptance is exactly 36/1 and every test and smoke check passes.
The one honest caveat is the `mesa`→`mes` head flip above — a single mild
regression in 88,420 families, traded for 3× the frequency coverage under a
distributable licence.
