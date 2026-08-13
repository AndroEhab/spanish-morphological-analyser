# Design Implementation Plan — Analizador Morfológico del Español

**Source of truth:** `design.md` (UI spec, 1,918 lines) + `spanish_morphological_analyzer_product_structure.md` (product spec, 2,350 lines) + `design_UI.png` (mockup, 1535×1024). All quotes below cite line numbers in those files.

**Status of every number in this document:** numbers marked **[measured]** were produced this session by read-only queries against `data/morph.sqlite` (2026-08-14 build, 117,253 lemmas / 1,256,152 forms / 80,760 families) or a read-only streaming pass over `kaikki.org-dictionary-Español.jsonl` (the 1.31 GB Spanish-edition file already at the repo root). Numbers marked **[doc]** come from `docs/ESWIKT_COMPARISON.md` or `docs/OPPORTUNITY_DATA.md`. Nothing was changed; no code was written.

---

## A. Section-by-section data mapping

Every panel in the mockup/specs, what it needs, whether we have it, and where from. "Have" = queryable from `data/morph.sqlite` today with the shape the UI needs.

### A0. Header — search, Analizar, Resultados recientes, theme toggle

| Sub-element | Needs | Have today? | Source / what it takes |
|---|---|---|---|
| Search field + dropdown | form candidates, tiered, frequency-ranked | ✅ yes | `GET /api/search` — unchanged contract. |
| **Analizar button / Enter submits** | resolve a typed string to an analysis | ⚠️ partially | The app today has **no free-text submit** (README: "there is no free-text submit — analysis is only ever triggered by selecting a concrete form"). The data fully supports resolution: exact folded form → rank lemmas by `freq` desc (`form.freq`, `lemma.freq`), fall back to citation-form match. Needs a new `word` parameter on `/api/analyze` (D) and is a deliberate behaviour change — see F4. |
| Resultados recientes | last N analyzed words | ❌ no | Pure client state — `localStorage` list of lemmas. No API needed. design.md §47/§54, product spec §47. |
| Theme toggle (dark mode) | palette swap | ❌ no | CSS-only; palettes in design.md §55. No API. |
| Deep link `/analyze/<word>` | stable route per form/lemma | ⚠️ partial | Current links are `/api/analyze?id=<numeric form id>` — **ids are rebuild-unstable**. Word-based resolution needed (D). design.md §75, product spec §75. |

### A1. Sidebar (7 items: Análisis, Familia de palabras, Origen, Derivados en inglés, Mnemotecnia, Favoritos, Ajustes)

Navigation only — scrollspy/anchors to the six dashboard regions + favourites view + settings. No data. **Label conflict:** mockup says "Derivados en inglés"; design.md §29 says the term "English Derivatives" must be avoided — see F3.

### A2. Card 1 — Análisis morfológico

| Row | Needs | Have today? | Source |
|---|---|---|---|
| Word (`hablábamos` 🔊) | the searched surface form; audio | form: ✅; audio: ❌ | `selected.form`. Audio is **1.9% coverage** — gap B4. |
| Summary line (`verbo · modo indicativo · pretérito imperfecto · 1ª persona del plural`) | grammatical interpretation in **Spanish** | ✅ data, ❌ language | `form.features` is a **closed English vocabulary** (`pipeline/tags.py` `humanize`: person/tense/mood/number/gender/formality/voseo/aspect/variant/clitic groups). `hablábamos` → `"imperfect indicative, 1st plural"`. A static features→Spanish mapping table (closed set, ~40 strings) yields exactly the mockup line. No new data. |
| Lexema `habl-` | surface-form stem | ✅ derivable — gap B1 | Closed desinence inventory `_DESINENCES` in `pipeline/paradigm.py`, matched accent-insensitively and feature-guided (`app/enrich.py`; pipeline untouched). `hablábamos` → `habl-` + `-ábamos` [verified in the shipped implementation]. |
| Morfema flexivo `-ábamos` | the stripped desinence | ✅ derivable | same mechanism; label from the form's features (`pretérito imperfecto, 1ª persona del plural`). |
| Base `hablar` | lemma | ✅ | `selected.lemma`; `form.is_lemma`. |
| Categoría `Verbo` | POS | ✅ | `selected.pos` → Spanish label table (`_POS_LABELS` in `app/store_sqlite.py` is English; Spanish labels are a static table). |
| Conjugación `Primera (-ar)` | conjugation class | ✅ derivable | Infinitive ending of the citation form (`-ar`/`-er`/`-ir`). The mockup's description column ("hablar, cantar, caminar…") is hand-authored; we can fill it with sibling verbs from the same paradigm residual bucket (`pipeline/paradigm.py` `compute_paradigm_key` — already persisted logic, not persisted data; a small lookup on rebuild) or drop the examples. |
| Ver descomposición morfológica (accordion: `habl + á + ba + mos`) | **morpheme-level** segmentation (stem + theme vowel + TAM + person/number) | ❌ no — gap B1 | The closed inventory encodes desinences as **atomic strings**, not slot decompositions. A 4-slot split needs a hand-authored `desinence → (theme vowel, TAM, person/number)` table (~150 entries, regular verbs only) or a simplified 2-way accordion. product spec §13 explicitly permits variation: *"The exact segmentation may vary by linguistic model."* |
| Ambiguity ("Most likely analysis / Other possible analysis (1)") | ranked alternative analyses | ✅ | Homonymous forms share a surface form across lemmas (`form` rows + `lemma_id`); ambiguity already computed in `search` (`qualifier`). Ranking by `freq` desc. design.md §16, product spec §15. |

### A3. Card 2 — Familia de palabras (radial hub)

| Sub-element | Needs | Have today? | Source |
|---|---|---|---|
| Hub node (`hablar`) | family head | ✅ | `family.head`; `derivation` root. |
| 6–10 satellite nodes (`hablante`, `habladuría`, `hablador`, `hablado`, `inhablable`, …) | curated preview of members | ✅ | `lemma.family_id` + `derivation` table (relation + label per member). Rank by relation type then `freq` (product spec §18 lists the curation criteria; frequency is the only one we have as data — see F11). |
| Count badge (mockup: `12`) | family size | ✅ | `family.size`. **Note: `hablar`'s real family is 25 members [measured], not the mockup's 12** — the mockup is illustrative. Families ≥6 members: 1,975; ≥10: 860 [measured]. |
| Searched-form highlight (`hablábamos` as a tinted node) | is-selected flag | ✅ | `tree.nodes[].is_selected` already exists; reuse for the preview. design.md §18. |
| Click a node → relationship (`hablador` — "derived from hablar + -dor", type, meaning) | relation label + gloss | ✅ | `derivation.label` (`hablar + -dor`) + `lemma.gloss` (English — see F2). |
| Ver toda la familia (Layer 3) | full family browser with filters | ✅ | Existing left-to-right map view (`familyMapView` in `app/static/app.js`, hover-path + zoom) + `tree` payload + `family.groups`. See F1. |
| Mobile: chip list instead of radial | same data, different layout | ✅ | product spec §56. |

### A4. Card 3 — Origen

| Sub-element | Needs | Have today? | Source |
|---|---|---|---|
| `Del latín` + etymon (`fabulare`) | source language + source form | ✅ | `etymon` table: `lang`/`lang_label`/`word`. **Coverage: 37,978 of 117,253 lemmas (32.4%) have any etymon row; 20,475 cite a Latin-family (`la*`) etymon [measured]** — the card is empty for ~2/3 of words; the §35 empty state ("No reliable historical origin is currently available.") is the contract for those. |
| Gloss `hablar, conversar, decir cuentos` | **Spanish gloss of the Latin word** | ❌ no | No table carries glosses for Latin etymons. The ES Spanish section has no etymology glosses (prose only, e.g. "Del latín errare." [doc]). Options: es.wiktionary's Latin section (unverified), en.wiktionary Spanish-entry etymology prose (English glosses — contradicts the Spanish UI), or omit the line. See B4/F7. |
| Evolution chain `fabulare → fablar → hablar` | ancestor chain | ✅ | `etymon` rows per lemma (depth 0 = immediate ancestor). Verified for `hablar`: `fablar (osp, inherited)` ← `fabulor (la)` ← `fābulārī (la)` [measured]. The API's `ancestry` already emits this newest-first. **Cosmetic mismatch:** the mockup writes `fabulare`; the DB's actual cited forms are `fabulor` / `fābulārī` — see F6. |
| Step notes (`f → h`, "¿Por qué la f se convirtió en h?") | per-transition explanation | ❌ no | design.md §22 says clicking a transformation reveals an explanation. We have `mode` (inherited/borrowed/…) and `note` (only 4 rows in the corpus carry a decomposition note [pipeline/README]) — no sound-change prose anywhere. The explanation text would be hand-authored per transition type (closed set: f→h, e.g. ~10 common sound changes) or omitted. |
| Ver evolución histórica (Layer 3) | deeper etymology | ⚠️ partial | `etymon` rows beyond the 8-cap already exist in the table; the API caps `ancestry` at 8 (incl. the word itself, at most one proto row). A full etymology view can read the full chain + proto rows. |

### A5. Card 4 — Cognados en inglés

| Sub-element | Needs | Have today? | Source |
|---|---|---|---|
| Intro (`Palabras en inglés emparentadas con el latín fabulare`) | root statement | ⚠️ root exists, English words don't | The Spanish side (`shared_etymon` from `cousins`) exists. The English side is **the B2 gap**. |
| Chip `fabulare → English clues` | root | ✅ | from `etymon` norm. |
| Cognate rows (`fable`, `fabulous`, `affable`, `confabulate`) + Spanish gloss + 🔊 | English lexicon with Latin ancestry + Spanish gloss + audio | ❌ no | Requires the English kaikki edition (2.9 GB, 1,351,351 entries, same postprocessed format [web, kaikki.org]) + a gated join. **The mockup's exact set is NOT reachable by an exact etymon join** — see B2. English-word audio: en.wiktionary has audio for a large share of English entries, unmeasured; Spanish glosses for English words: not available anywhere in our data (would need translation or the es.wiktionary English section — unverified). |
| Ver más cognados | more items | ❌ | Phase 3. |

### A6. Card 5 — Mnemotecnia

| Sub-element | Needs | Have today? | Source |
|---|---|---|---|
| Text (`Si "hablar" viene de "fabulare"…`) | memory aid | ❌ no — gap B3 | Not derivable from any dictionary data. Options in B3. |
| Illustration (two figures + speech bubble) | image asset | ❌ no | design.md §27: illustrations are "may use" (optional). No data source; an image-generation step is out of scope of the analyzer's data model. Recommend omitting or static hand-made assets. |
| Ver más mnemotecnias | 2+ per word | ❌ | only with generation/hand-authoring (B3). |

### A7. Bottom strip — Otras formas del verbo

| Sub-element | Needs | Have today? | Source |
|---|---|---|---|
| 6–8 forms (`hablo hablas habla hablamos habláis hablan hablé`) + feature line (`pres. ind. 1ª sing.`) | present-indicative paradigm | ✅ | `form` rows + `features`. All 7 mockup forms exist for `hablar` with their features [measured]. 8,461 of 11,779 verb lemmas have present-indicative rows [measured]. Selection: same-tense paradigm preferred (product spec §39); fallback to highest-freq forms. |
| Ver conjugación completa (Layer 3) | full paradigm | ✅ | The existing POS-grouped list view with bucketed paradigm sections is exactly this — reuse as the deep view (F1). |

### A8. Favoritos

| Sub-element | Needs | Have today? | Source |
|---|---|---|---|
| Save lemma / family / mnemonic | storage | ❌ no | Client-side `localStorage` keyed by lemma (default favorite = the lemma, not the searched form — product spec §48). No API. |

### A9. Glosses (everywhere)

Every card that shows a word can show a gloss. Today: English (`lemma.gloss`, en.wiktionary). The mockup shows Spanish glosses. ES-edition Spanish glosses cover **48,350 of 106,907 distinct lemma words (45.2%) [measured]** — see B4 and the F2 owner decision.

---

## B. The four gap verdicts

### B1 — Morphological decomposition (Lexema / Morfema flexivo): **derivable as a two-way LOOKUP from the existing closed inventory, but the raw `_strip_desinence` is NOT display-safe — the shipped splitter adds feature-guided selection, clitic verification and stem corroboration**

**What exists.** `pipeline/paradigm.py` carries `_DESINENCES`, a closed inventory of ~120 Spanish verbal desinences, used by `_strip_desinence(form)`: longest-desinence match, ≥3-char-stem guard, returns the original-form prefix as stem. It is the same machinery that computes E2 allomorphs; it is deliberately "used ONLY for stripping, never building" (paradigm.py docstring).

**Correction to the earlier draft of this plan.** The raw function is NOT usable for display, for two measured reasons:
1. **Accent mismatch:** it folds the *form* but not the *inventory entries*, so accented desinences never match. `hablábamos` → `habláb + -amos` (the `-ábamos` entry never matches the accent-free folded form; the greedy match takes `-amos`); `habláis` → `hablái + -s`; `hacía` → `hací + -a`.
2. **Participle over-strip on finite forms:** the greedy longest match carves the participle desinences (`-to/-do/-so/-cho`) off everyday present forms — `canto` → `can- + -to`, `mando` → `man- + -do`, `miento` → `mien- + -to`, `gusto` → `gus- + -to`.

**What Phase 1 actually ships** (implemented in `app/enrich.py`, pipeline untouched): the *same* closed `_DESINENCES` set (imported; an import-time assert pins the two together so they cannot drift), with three selection guards that keep every emitted split a verified lookup rather than a guess:
- **Accent-insensitive matching on both sides** — `hablábamos` → `habl- + -ábamos`, `habláis` → `habl- + -áis`, `hacía` → `hac- + -ía`, exactly the mockup's example.
- **Feature-guided cell selection** — the desinence must be consistent with the form's own analysis (cell groups transcribed verbatim from the inventory's comment grouping in paradigm.py): `canto` (present indicative) must split with a present-indicative desinence, so `-to` is excluded → `cant- + -o`; `miento` → `mient- + -o`; `hecho` (participle) → the participle cell, but the `-cho` match leaves a 2-char stem so the split is rejected → `lexeme: null` (honest empty state for irregular participles).
- **Clitic verification against the lemma's own form table** (ruling F9): trailing enclitics are stripped only when every intermediate is a known form of the same lemma (`mentirlo` → base `mentir` → `ment- + -ir`; `comprándomelos` → `compr- + -ando`). Unverifiable chains and clitic-marked surfaces yield null (`démoslo`, `dese` = `dé+se` under dar, `vete` under ir) rather than a mis-segmentation; clitic-lookalike surfaces (`hablo` ends in `-lo`) fall through to the plain split only with same-lemma stem corroboration.

**Measured error surface.** Of 491,173 clitic form rows in the DB: 473,944 (96.5%) have a fully verifiable clitic chain; of the remainder only 50 rows (0.01%) would produce any naive split at all, and all 50 sampled are multi-word idiom surfaces (`teneos en cuenta`, `estándola chiñando`, …) that the junk guard already nulls. The participle over-strip, the accent bug, and the unverifiable-clitic cases above are all eliminated by construction; the residual nulls are short-stem irregulars (`soy`, `doy`, `voy`, `estoy`, `fue`, `di`, `dio`) and irregular participles (`hecho`), which render the §35/§36 partial-state rather than a wrong split.

**Still NOT available: the 4-slot accordion** (`habl + á + ba + mos` with stem/theme-vowel/TAM/person-number labels, design.md §15). `_DESINENCES` stores desinences as atomic strings; the internal slot boundaries exist only as linguistic knowledge, not data. Building it = a hand-authored desinence→slots table (~150 regular entries) as new pipeline data, or a simplified 2-way accordion (stem + whole desinence) which the docs explicitly tolerate (product spec §13: "The exact segmentation may vary by linguistic model").

**Verdict: the 2-way split is shipped server-side (Phase 1) as a verified lookup; the 4-slot accordion stays behind the same button with the 2-way split until slot data exists.**

### B2 — English cognates: **confirmed the largest gap, and the mockup's example set is NOT reachable by an exact-etypon join — it needs a new gated same-root join on Latin**

**The mockup's claim.** `hablar ← fabulare → fable, fabulous, affable, confabulate`.

**What our data actually cites [measured]:**
- `hablar`'s ancestry: `fablar (osp)` ← `fabulor (la)` ← `fābulārī (la)` — norms `fablar`, `fabulor`, `fabulari`.
- `fábula` (a member of hablar's family, relation `derived`) cites `fābula` (norm `fabula`, borrowed). `fabular` (verb, also in hablar's family) cites `fabulor`/`fabulārī`.

**What the English words cite** (en.wiktionary etymology, same template system): `fable` ← Latin `fabula`; `fabulous` ← `fabulosus`; `affable` ← `affabilis`; `confabulate` ← `confabulatus`. None of these norms appear in hablar's own chain.

**Consequence.** An exact-`norm` join (the strongest signal the pipeline already uses for cousins) produces **no cognates for hablar** and would route `fable` to `fábula` instead. The mockup's set arises only from a **same-Latin-root join** — `fabula/fabulor/fabulari/fabulosus/confabulatus` share the 4-char root `fabul-`; `affabilis` shares it only after undoing the `ad-`→`af-` assimilation (and even `_LATIN_PREFIXES` stripping leaves `fabilis`, so `affable` fails a ≥4-char gate and passes only a ≥3-char one). That join is **new matching logic on Latin forms** — the project's hard rule "never invent morphology by pattern-matching" applies with full force; the pipeline already does gated Latin matching in E3/E4b (first4 overlap, ≥3-char allomorph, no truncated stems, disjoint-ancestor, prefix gates — all measured to ~60–97% precision, see pipeline/README), so a cognates gate can follow that precedent, but it must be designed and measured, not bolted on. `mensa`/`mensis`/`mens` (table/month/mind) show why ungated 4-char roots conflate families.

**Scale.** 20,475 lemmas cite a Latin-family etymon; 14,764 distinct Latin norms (10,415 cited by exactly one lemma; 44 by 21–60; 6 by >60) [measured]. The English edition is a **2.9 GB / 1,351,351-entry postprocessed JSONL** in the identical format our pipeline consumes [web, kaikki.org/dictionary/English]. It exposes `etymology_templates` (the same 219-template vocabulary the Spanish section of en.wiktionary uses — 62,975 entries there carry them [doc]); the count of English entries citing `la*` etymons is **unmeasured** and needs a streaming pass (procedure in E3). Download at typical 3 MB/s ≈ 15 min; a full streaming pass ≈ 1–2 min.

**Estimate.** Exact-norm joins will yield tens of thousands of (Spanish etymon → English word) pairs only if English entries cite the same Latin lemmas our Spanish words cite — partial (English Wiktionary's Latin citations are richer than ours but differently shaped: `bor|en|la|factorium` vs our `inh|la|facere`). The mockup-grade result (fable/fabulous/affable/confabulate under hablar) requires the gated root join. **Honest floor: this phase ships an empty state for most words unless the gate work is done and measured; the docs' §52 rule exists precisely for this.**

### B3 — Mnemonics: **not derivable from any dictionary; four options, and the product spec tells us which one it wants**

The spec is explicit that mnemonics must reuse the page's real relationships: product spec §67: *"Mnemonics should preferably derive from real information already on the page. Preferred sources: 1. English cognate 2. Latin root 3. recognizable Spanish derivative 4. morphological structure 5. semantic evolution. Arbitrary sound-alike mnemonics should be a fallback, not the default."* And §35: *"The product should prefer true linguistic relationships over arbitrary invented associations whenever possible."*

Options, with cost:

1. **Data-driven templates (recommended first)** — a template engine over fields the analysis already returns: `hablar ← fābulārī` (origin) + `fable` (cognate) → "hablar viene del latín fābulārī; fable viene de la misma raíz; una fable es una historia que se cuenta". Zero new data, satisfies §67's preferred sources, deterministic and auditable. Coverage mirrors origin/cognate coverage (32.4%/Phase 3). Cost: 2–3 dev-days. This is what "Show another mnemonic" would cycle through (2–4 variants per template set).
2. **LLM generation offline into a table** — prompt per lemma (or batch) with the etymology/cognate/family context, stored in a `mnemonic` table. Cost: token budget (top-10k lemmas ≈ tens of millions of tokens at current rates, a few $–tens of $), a generation+review pass, and it introduces **generated content** into a CC BY-SA 4.0 database — licensing and attribution questions the repo has so far avoided (see F10). Quality must be reviewed; the docs' acceptance criteria (§84: "short, uses information from the analysis") are a review checklist, not a guarantee.
3. **Hand-authoring the top-N** — e.g. the 1,130 lemmas with freq > 100 [measured; OPPORTUNITY_DATA.md §6] is a realistic 3–5 day writing task; beyond ~2k words it stops scaling.
4. **Omit** — the §35/§51 empty states exist for exactly this; a mnemonic card with no content is a supported state.

Recommendation: ship (1) in Phase 1–2 (it needs only data we have), treat (2)/(3) as optional Phase 4 enrichment. Do not ship sound-alike fallbacks as the default — the spec forbids it.

### B4 — Audio + Spanish glosses: **importable now; audio 1.9%, Spanish glosses 45.2%; the ES edition also lacks Latin glosses**

Measured this session against the already-downloaded `kaikki.org-dictionary-Español.jsonl` (1.31 GB, 854,082 entries, 150,650 lemma entries; one full streaming pass = 18 s) [measured]:

| metric | value [measured] |
|---|---|
| lemma entries with audio | 2,801 (2,157 distinct words) |
| lemma entries with IPA | 150,335 (99.8% of lemma entries) |
| lemma entries with a gloss | 145,863 (137,172 distinct words) |
| our DB lemmas with an ES **Spanish gloss** | 48,350 / 106,907 distinct lemma words (**45.2%**) |
| our DB lemmas with ES **audio** | 1,999 (**1.9%**) — 1,294 of the 13,985 freq≥1 words |
| ES edition structured etymology | **zero** — 0 `etymology_templates` in the whole file [doc, ESWIKT_COMPARISON.md] |

`hablar` itself: has audio (`LL-Q1321 (spa)-Rodrigo5260-hablar.wav`, with `mp3_url`/`ogg_url`) and Spanish glosses ("Expresar algo usando palabras de viva voz.") [measured]. So the mockup's panel is fully satisfiable *for the words that have it*.

**Cost of the targeted import.** The file is already on disk. A read-only pass takes 18 s [measured]; writing a derived side table (`es_word` keyed by folded word → `{gloss, audio_urls, ipa, tag}`) adds ~10–20 MB to the DB and ~1 min to the 2-min build (the whole unused-value bundle of the EN edition was measured at ~45 MB [doc, OPPORTUNITY_DATA.md §7]). 3–4 dev-days total, touching only `pipeline/build.py`-adjacent extraction + a new table + store reads. The family algorithm is untouched — this is exactly the "re-download and import only sounds/etymology_texts as a secondary table" option ESWIKT_COMPARISON.md already blessed (its §4e).

**Two honest limits.**
- **Audio at 1.9%**: the speaker icon shows for ~1 in 50 analyses. The docs make this a supported state (product spec §49: *"Where pronunciation is available, audio belongs close to the primary word. It should remain a secondary action."*), but the mockup's density (audio on the word AND on every cognate) will rarely be real. Cognate (English) audio is a Phase 3 concern from the English edition, unmeasured.
- **The origin card's Latin gloss** (`Del latín fabulare — hablar, conversar, decir cuentos`) is a **fifth, hidden gap**: it needs a *Spanish* gloss of the *Latin* word, which neither our EN-edition data nor the ES Spanish section provides (ES etymology is prose with no glosses [doc]). Candidates: es.wiktionary's Latin section (existence/coverage unverified), en.wiktionary Spanish-entry etymology prose (English glosses — contradicts the all-Spanish UI), or drop the gloss line and show the chain only (design.md §21's default card shows "rough source meaning" — dropping it loses a stated element). Owner decision (F7).

---

## C. What the docs say about missing data — the behaviour contract

These rules decide how every gap above is presented. Quoted verbatim.

**Empty states (design.md §35, lines 1161–1177):**
> If no etymology exists:
> "No reliable historical origin is currently available."
> If no English cognates exist:
> "No useful English root relatives found."
> Do not force weak or speculative relationships purely to fill the card.

**Error states (design.md §36, lines 1179–1200):**
> Example: "We couldn't analyze "xyzabc"." — Try: • checking the spelling • searching the base form
> If partial data exists, show it rather than failing the entire page.
> Example: "Morphology available / Etymology unavailable"

**Graceful degradation (product spec §50, lines 1513–1538):**
> If the word is not recognized: "We couldn't confidently analyze "x"." — Try: checking the spelling / searching the lemma
> If partial information exists, show it. … The page should not fail as a whole because one enrichment source is missing.

**Missing family (product spec §51, lines 1540–1554):**
> If no reliable family can be produced: "No reliable word family is available for this entry yet."
> Do not fill the space with speculative relationships. The same rule applies to cognates and etymology. Accuracy is more important than visual completeness.

**Missing cognates (product spec §52, lines 1556–1568):**
> The product should explicitly allow: "No useful English root relatives found."
> This is preferable to showing weak, remote, or misleading relationships.

**Confidence (design.md §25, lines 879–894; product spec §53, lines 1570–1590):**
> If the data contains confidence information, it may be represented as: Direct cognate / Shared Latin root / Related learned borrowing / Possible historical relation.
> Avoid percentages unless the underlying data genuinely supports numerical confidence.
> Useful labels: Most likely / Alternative analysis / Possible historical relation / Disputed origin / Uncertain.

**Ambiguity (design.md §16, lines 580–607; product spec §15, lines 634–669):**
> Most likely analysis … Other possible analysis (1). Never display all possible analyses equally unless confidence is unavailable. … The product should avoid pretending uncertainty does not exist. It should also avoid making ambiguity the first thing a learner sees.

**Partial/incremental states (product spec §61–63, lines 1739–1823):**
> Empty / Loading / Complete / Partial / Ambiguous / Error states … the layout should remain recognizable across states.
> The user should see results incrementally if different sections become ready at different times. … The product should not hide an already-useful morphological result while waiting for etymology.

**Audio is optional-when-present (product spec §49, lines 1501–1511):**
> Where pronunciation is available, audio belongs close to the primary word. It should remain a secondary action. Audio should not be duplicated across every related node by default.

**Mnemonics must use real relationships (product spec §67, lines 1932–1946):** quoted in B3; plus §36–37 (lines 1170–1203): one mnemonic by default; "Show another mnemonic" replaces in place; the card should not accumulate mnemonics vertically.

**Family vs conjugation separation (product spec §65, lines 1861–1901):**
> Word family: hacer, hacedor, deshacer, rehacer, hecho, hechura. Conjugation: hago, haces, hace… Inflected forms can appear in the family context when relevant … but they should not dominate the family view. The product must preserve the distinction between same lexical family and same lexeme, different grammatical form.

**Preview is curated (product spec §18, lines 725–742):**
> The preview should not simply show the first N items returned by a data source. A word-family preview is curated product output. (Ranking considerations: frequency, semantic transparency, closeness to the lemma, usefulness to learners, morphological diversity, confidence.)

**Sections may be empty independently (product spec §64, lines 1825–1859):** each section owns a job and may be absent; nothing forces another section to compensate.

**Acceptance test for the whole dashboard (product spec §79, lines 2203–2217):** the default screen must answer 7 questions (word, base form, grammar, several related words, historical origin, useful English connection, memory connection) — and §86.9: *"Missing data should be admitted rather than filled with weak guesses."*

---

## D. Proposed API additions

**Contract rules:** `/api/search` unchanged. `/api/analyze?id=` unchanged in every existing key (`selected`, `family`, `tree`, `ancestry`, `cousins`) — the current UI keeps working. All new keys are **additive and nullable**; a null/empty value is the render trigger for the empty states in §C. New keys must be added to **both backends** (`app/store_sqlite.py` and `app/store_fixture.py` — tests force the fixture), which conveniently makes the fixture the empty-state test harness.

**Implementation status (Phase 1, 2026-08-14):** `query`, `selected.audio/ipa` (null), `morphology` (incl. `alternatives`), `familyPreview`, `origin`, `nearbyForms`, `englishRelatives` (null), `mnemonics` (null), and the `word` parameter are live in both backends with the shapes below. `origin.stages` is emitted newest-first (the Spanish word first, etymons backwards in time — "oldest last"), matching the example. `morphology.categoría`/`conjugación` are Spanish aliases of `posLabel`/`conjugationClass`.

**New deep-link resolution (design.md §75, product spec §75):**
```
GET /api/analyze?word=hablábamos        # NEW — resolves a typed string
GET /api/analyze?id=12345               # unchanged — existing entry ids
```
Resolution order: (1) exact folded `form` rows → rank by `freq` desc, `is_lemma` desc; (2) exact folded `lemma.word` (citation); (3) none → 404 (client shows the §36/§50 error state). Multiple lemmas for one form → top result returned, the rest as `morphology.alternatives` (ambiguity, §C).

**Proposed `GET /api/analyze` response** (new keys marked NEW; example values from `hablábamos`, verified real data):

```jsonc
{
  "query": "hablábamos",                    // NEW — echoes the resolved word
  "selected": {
    "id": "12345", "form": "hablábamos", "lemma": "hablar", "pos": "verb",
    "gloss": "to speak; to talk; …",        // unchanged, still English (F2)
    "features": ["imperfect indicative, 1st plural"],
    "audio": null,                          // NEW — {mp3_url, ogg_url, tag} | null (Phase 2)
    "ipa": null                             // NEW — string | null (Phase 2)
  },

  // NEW — morphology card (Phase 1). Mirrors design.md §49 AnalysisResult.morphology.
  "morphology": {
    "posLabel": "verbo",                    // Spanish POS label
    "summary": "verbo · modo indicativo · pretérito imperfecto · 1ª persona del plural",
    "lexeme": "habl-",                      // 2-way desinence split (B1) | null
    "inflection": "-ábamos",                // | null
    "conjugationClass": "Primera (-ar)",    // from citation-form infinitive | null (non-verbs)
    "decomposition": [                      // "Ver descomposición morfológica" accordion
      { "segment": "habl",  "label": "raíz o base léxica",                 "kind": "stem" },
      { "segment": "-ábamos", "label": "desinencia de pretérito imperfecto, 1ª persona del plural", "kind": "desinence" }
    ],
    "alternatives": [                       // ranked ambiguity; [] when unambiguous
      { "lemma": "…", "pos": "…", "summary": "…", "entry_id": "…" }
    ]
  },

  "family": { "head": {…}, "note": null, "groups": [ … ] },   // unchanged

  "tree": { "root_lemma_id": 5311, "nodes": [ … ] },          // unchanged (full family, Layer 3)

  // NEW — radial preview (Phase 1). design.md §17-18 / product spec §17-19.
  "familyPreview": {
    "hub": "hablar",
    "totalCount": 25,                       // family.size
    "nodes": [                              // <=10, curated: relation-priority then freq
      { "lemma": "hablante", "pos": "noun", "relationLabel": "hablar + -ante",
        "gloss": "…", "isSelected": false },
      { "lemma": "hablábamos", "pos": "verb", "relationLabel": "", "gloss": "…",
        "isSelected": true }                // searched form highlight (design.md §18)
    ]
  },

  "ancestry": [ … ],                        // unchanged (existing ribbon still works)

  // NEW — origin card (Phase 1). design.md §21-22 / product spec §23-25.
  // Built from the same etymon rows as ancestry; null when no etymon exists (32.4% coverage).
  "origin": {
    "sourceLanguage": "latín",
    "sourceWord": "fābulārī",               // deepest usable non-proto step
    "sourceMeaning": null,                  // Phase 2 (Latin gloss — see B4/F7) | null
    "stages": [                             // oldest last, like the mockup chain
      { "word": "hablar",   "lang": "es",   "langLabel": "español",         "mode": null,       "note": null },
      { "word": "fablar",   "lang": "osp",  "langLabel": "español antiguo", "mode": "inherited", "note": null },
      { "word": "fabulor",  "lang": "la",   "langLabel": "latín",           "mode": "inherited", "note": null },
      { "word": "fābulārī", "lang": "la",   "langLabel": "latín",           "mode": "inherited", "note": null }
    ]
  },

  "cousins": { … },                         // unchanged

  // NEW — English cognates (Phase 3; null before, per §52). design.md §50 shape.
  "englishRelatives": null | {
    "sharedRoot": "fabul-",
    "items": [
      { "word": "fable", "gloss": "cuento…", "sharedRoot": "fabul-",
        "relationType": "shared-latin-root", "explanation": "…", "audio": null }
    ]
  },

  // NEW — mnemonic (Phase 4; null before, per §35/§51). design.md §52.
  "mnemonics": null | [
    { "text": "…", "source": "latin-root" }   // source ∈ latin-root|cognate|family|morphology
  ],

  // NEW — other-forms strip (Phase 1; verbs only). design.md §28-29 / product spec §38-39.
  "nearbyForms": [
    { "form": "hablo",    "features": "present indicative, 1st singular", "isLemma": false },
    { "form": "hablas",   "features": "present indicative, 2nd singular", "isLemma": false },
    { "form": "habla",    "features": "present indicative, 3rd singular", "isLemma": false },
    { "form": "hablamos", "features": "present indicative, 1st plural",   "isLemma": false },
    { "form": "habláis",  "features": "present indicative, 2nd plural",   "isLemma": false },
    { "form": "hablan",   "features": "present indicative, 3rd plural",   "isLemma": false }
  ]
}
```

Notes:
- `nearbyForms` selection rule (product spec §39): same-tense paradigm of the searched form when it is a verb form; else the lemma's present-indicative row; capped at 6–8. For non-verbs the key is `[]` and the strip renders nothing (the docs scope the strip to verbs).
- The existing `ancestry`/`cousins` keys are kept as-is so the current ribbon/cousins UI survives; `origin` is the product-facing shape (design.md §49's `etymology`). A future cutover may fold `ancestry` into `origin`; not now.
- No new endpoints are strictly needed for recent results or favourites — both are client-side (`localStorage`, product spec §47–48). Settings likewise (theme = CSS class).
- Spanish display strings (labels, feature→Spanish summary, POS labels) live in a closed static mapping table in the store (or client); nothing new is queried.

---

## E. Phasing

Each phase ends shippable and verifiable. **Phase 1 needs only data we have today.** New datasets/generation are flagged.

### Phase 1 — Spanish dashboard on existing data (no new datasets)
**Shippable:** the full mockup layout minus the three data-dependent enrichments (cognates, mnemonic, audio) and minus the Latin gloss; every card renders from the current DB, with the §C empty states where data is absent.
- Spanish UI shell: header (logo, search + Analizar, Resultados recientes, theme toggle), 7-item sidebar, 12-column card grid, dark mode, responsive (design.md §5–11, §37, §55, §58).
- Morphology card: summary line (features→Spanish map), table (lexeme/morpheme 2-way split per B1, base, categoría, conjugación), decomposition accordion (2-way; 4-slot optional), ambiguity ranking.
- Family radial preview (`familyPreview`), searched-form highlight, node-click relationship popover, "Ver toda la familia" → existing map view.
- Origin card: chain from `etymon` (no `sourceMeaning`), empty state at 32.4% coverage.
- Other-forms strip (verbs) + "Ver conjugación completa" → existing list view.
- Recent results, favourites (localStorage), deep links (`word` resolution).
- **API work:** new `analyze` keys in both backends + `word` parameter; `tests/test_api.py` extensions for the new keys against the fixture (which exercises the empty states).
- **Size:** ~10–14 dev-days (frontend-heavy; API ~2 days incl. tests). **Verification:** UI smoke test on real DB + fixture; acceptance criteria product spec §79–85.

### Phase 2 — Spanish edition import: audio, IPA, Spanish glosses (new dataset, already downloaded)
- Streaming pass over the on-disk 1.31 GB file (18 s measured), build `es_word` side table keyed by folded word: `{gloss, ipa, audio mp3/ogg urls, tag}`; ~1 min added to the build, ~10–20 MB DB.
- Store reads → `selected.audio`, `selected.ipa`; gloss fallback logic (F2 decision needed first).
- Licensing note in `docs/LICENSES.md` (CC BY-SA 4.0/GFDL — same class as current data, per README).
- **Size:** 3–4 dev-days. **Coverage:** audio 1.9%, Spanish gloss 45.2% [measured].

### Phase 3 — English cognates (new dataset: English kaikki edition, 2.9 GB)
- Download `kaikki.org-dictionary-English.jsonl` (~15 min at 3 MB/s); one streaming measurement pass first (procedure: count English lemma entries whose `etymology_templates` cite `la*`, extract cited Latin norms; ~1–2 min) — **do not design the join before this number exists**.
- Build `english_etymon` side table (English word, POS, gloss, cited Latin norms).
- Join design: exact-`norm` first (reuses the cousins semantics, zero new inference), then — only if precision is measured and acceptable — a gated root join on the E3/E4b precedent (Latin-only, prefix-strip, ≥3-char allomorph, fanout caps, first4 overlap). The project's "no invented morphology" rule means the root join is gated matching with a measured precision, or it doesn't ship; the §52 empty state ships regardless.
- **Size:** 8–12 dev-days incl. measurement, gates, and honesty checks. **Coverage:** unmeasured until the pass runs; exact-norm alone will be sparse (see B2 — hablar's own norms are cited by almost no English entries).

### Phase 4 — Mnemonics (generation/authoring; not from dictionary data)
- **4a (recommended, ~2–3 dev-days):** template mnemonics over origin/cognates/family — zero new data, §67-compliant. Ships with the empty state for words without etymology.
- **4b (optional, ~4–6 dev-days + review):** LLM generation offline into a `mnemonic` table for the top-N lemmas (or hand-authoring top ~1k) — needs a licensing decision (F10) and a quality pass against product spec §84.
- Deliberately after Phases 2–3 so templates can consume Spanish glosses + real cognates.

### Phase 5 — Layer 3 deep views (mostly reuse)
- Full family browser: existing left-to-right map (hover-path, zoom, collapse) promoted behind "Ver toda la familia" + filter toolbar (design.md §20, product spec §21–22).
- Complete conjugation: existing POS-grouped list view behind "Ver conjugación completa" (design.md §29).
- Full etymology view: uncapped `etymon` chain + proto rows (design.md §26).
- **Size:** 3–5 dev-days. No new data.

---

## F. Risks and conflicts

**F1 — Radial family panel vs the shipped left-to-right tree: they complement; the docs specify both.** design.md §17–18 and product spec §17–19 define the dashboard preview as a central lemma + 6–10 satellites (the radial mockup) — "The purpose of the preview is not completeness" (product spec §17). design.md §20 ("View entire family → opens either a large modal graph or a dedicated /family/hablar page") and product spec §21–22 define the full family as a spacious browser with filters, zoom, grouping — which is precisely what the existing map view (hover-path to root, zoom toolbar, +N collapse) already is. **No conflict in the docs; the product change is:** today the map/list IS the primary page; the redesign demotes both to Layer 3 behind the preview card. The existing POS-grouped list becomes the complete-conjugation deep view. The radial view replaces the dashboard family list; the tree payload (`tree`) is reused for both the preview (subset) and the full view (all nodes) — no new backend shape beyond `familyPreview`.

**F2 — Spanish UI vs English gloss data: the docs are silent; the owner must choose.** 100% of lemmas have an English gloss; 45.2% have a Spanish one [measured]. The mockup is all-Spanish. Three options: (a) Spanish gloss when available, English otherwise (mixed-language UI — the docs never discuss gloss language; product spec §50's "partial information" rule arguably supports it); (b) Spanish-only, empty gloss line where missing (pure UI language, but ~55% of words show no gloss — and gloss is Tier A identity content, product spec §6); (c) keep English glosses everywhere (consistent, but contradicts the mockup's Spanish). This decision gates Phase 2's gloss wiring. **Flagged for the owner.**

**F3 — Mockup label "Derivados en inglés" directly contradicts design.md §29** (lines 1008–1025): *"The term 'English Derivatives' should be avoided when it implies that the English word derives from the Spanish word."* The mockup's card title "Cognados en inglés" is consistent with the spec; only the sidebar item uses the banned term. Recommend the sidebar read "Cognados en inglés" (or the spec's "English Root Relatives" → "Relativos en inglés"). **Flagged.**

**F4 — Free-text submit is a hard reversal of a documented product rule.** README: "there is no free-text submit — analysis is only ever triggered by selecting a concrete form." design.md §7: "Enter submits", §33; product spec §8: "The analyzer should accept both lemmas and inflected forms." The data supports ranked resolution (D), and the ambiguity rules (§C) define how multi-lemma hits are shown, so the feature is buildable — but it changes a rule the README calls deliberate. **Owner sign-off wanted.**

**F5 — Cognates, if built with a root join, are "invented morphology" unless gated and measured.** The project's hard rule and the §51/§52 empty-state rules both point the same way: an ungated same-root join on Latin would put `mensa/mensis/mens` words together (table/month/mind). The E3/E4b history (pipeline/README: truncated stems rejected at ~60% precision; first4 gate added) is the precedent for how much care this needs. The exact-`norm` route is safe but sparse; the root route is rich but must earn its precision number. **This is the single most likely place the product promise (mockup-quality cognates) exceeds the data.**

**F6 — The mockup's `fabulare` ≠ our data's `fabulor`/`fābulārī`; the origin card must show the real cited forms.** The chain `fabulare → fablar → hablar` is a stylization; our table says `fablar (español antiguo) ← fabulor ← fābulārī (latín)` [measured]. Cosmetic, but the UI worker should build from `origin.stages`, not from the mockup strings.

**F7 — The origin card's Latin gloss (`hablar, conversar, decir cuentos`) has no source.** Not in the EN data, not in the ES Spanish section (prose, no glosses) [doc], not derivable. Candidates: es.wiktionary's Latin section (needs a download + verification it exists and covers our norms), en.wiktionary Spanish-entry etymology prose (English glosses — contradicts F2's Spanish-only goal), or drop the gloss line (design.md §21 lists "rough source meaning" as default content — dropping loses a stated element). **Flagged for the owner.**

**F8 — Family count badge: the mockup's `12` will often disagree with reality.** `hablar`'s family is 25 members [measured]; the badge should show `family.size`. 1,975 families have ≥6 members; 69,745 lemmas (59.5%) are singletons [measured] — the radial preview for those shows hub + empty ring + the §51 empty state.

**F9 — Clitic forms break the 2-way split** (B1 mode 3). The morphology card must not show a misleading split for `hacerme`-type searches; either strip clitics first (a small extension of the same closed inventory — clitics are a closed set: me/te/se/nos/os/le/les/lo/la/los/las) or emit `lexeme: null` and let the empty-state rules apply. Recommendation: extend the strip with the closed clitic set in the store layer, keeping the pipeline untouched (Phase 1 API-side concern only).

**F10 — Generated mnemonics change the licensing posture.** The DB is uniformly CC BY-SA 4.0 (README, docs/LICENSES.md); LLM-generated text has no clear provenance under that regime. Template mnemonics (4a) stay derivable from CC BY-SA data; LLM content (4b) needs an explicit decision before it enters any shipped table.

**F11 — "Curated" family preview vs what we can rank.** Product spec §18 lists five curation criteria; only frequency (and relation type, closeness via `derivation.depth`, morphological diversity via POS) are data. "Semantic transparency" and "usefulness to learners" are not. Phase 1 ranks by (relation type, freq, POS diversity) and accepts that as a first cut; flagging the judgment call rather than pretending the full §18 model is implemented.

**F12 — Minor data-quality notes for the UI worker.** `hablamos` carries a junk analysis "present preterite indicative, 1st plural" alongside the correct one [measured]; the Spanish summary mapper must pick the first/cleanest analysis, not join them. 75,915 form rows contain spaces or non-alphabetic characters (annotation strings like `o-ue alternation`) [measured] — the decomposition and strip code must never run on them. `meta` holds only `n_families`/`max_freq`; new tables should add counts there (health() already falls back to COUNT(*)).

**F13 — Nothing here forces a schema migration of the core four tables.** All Phase 1 features read existing columns. New tables arrive only in Phases 2–4 (`es_word`, `english_etymon`, optionally `mnemonic`), all additive, all display-only — the same posture the `etymon`/`derivation` tables already hold ("never feed back into family membership", pipeline/README).

---

## Report-back summary

- **B1 — Lexema/Morfema: derivable as a two-way LOOKUP** from the existing closed desinence inventory, but the raw `_strip_desinence` is not display-safe (accent mismatch: `hablábamos` → `habláb-`; participle over-strip: `canto` → `can-`). The shipped splitter (docs B1) uses the same inventory with accent-insensitive matching, feature-guided cell selection, clitic verification against the lemma's own forms, and stem corroboration — every split is a verified lookup. Error surface measured: 96.5% of 491k clitic rows verify; residual nulls are short-stem irregulars and irregular participles (rendered as empty states). The 4-slot accordion (`habl+á+ba+mos`) still needs a hand-authored desinence→slot table.
- **B2 — English cognates: confirmed the largest gap; the mockup's exact set is unreachable by an exact-etypon join** (hablar cites `fabulor/fābulārī`; the English words cite `fabula/fabulosus/affabilis/confabulatus`). Needs the 2.9 GB English edition + a **gated, measured** root join on the E3/E4b precedent; exact-norm joins alone will be sparse. 20,475 lemmas cite Latin etymons today; English-side counts unmeasured until the file is streamed.
- **B3 — Mnemonics: not derivable from data.** Options: data-driven templates (recommended, §67-compliant, zero new data), LLM/hand-authored top-N (licensing + review cost), or omit with the §35/§51 empty state. Sound-alike fallbacks are spec-forbidden as defaults.
- **B4 — Audio + Spanish glosses: importable now.** ES edition already on disk; one 18 s pass [measured] gives audio for **1.9%** of our lemmas and Spanish glosses for **45.2%**; zero structured etymology [doc]. 3–4 dev-days. Hidden fifth gap: a **Spanish gloss of the Latin etymon** (origin card) has no source (F7).
- **C — Missing-data rules:** §35/§36/§50/§51/§52 empty and error strings (verbatim in §C), §25/§53 confidence labels, §16/§15 ambiguity ranking, §61–63 incremental states, §49 audio-as-secondary, §67 mnemonic sourcing, §65 family-vs-conjugation separation, §86.9 "Missing data should be admitted rather than filled with weak guesses."
- **E — Phases:** P1 Spanish dashboard on today's data (10–14 d); P2 ES import: audio/IPA/glosses (3–4 d, new dataset on disk); P3 English cognates (8–12 d, new 2.9 GB dataset, gate design + measurement); P4 mnemonics (2–3 d templates, +4–6 d optional generation); P5 deep views (3–5 d, reuse). Phase 1 needs no new data.
- **F — Conflicts:** F1 radial vs tree (complement — preview vs Layer 3, no spec conflict); F2 gloss language (owner decision); F3 "Derivados en inglés" label contradicts design.md §29; F4 free-text submit reverses a documented rule (owner sign-off); F5 root-join cognates risk invented morphology; F6 mockup `fabulare` vs data `fabulor/fābulārī`; F7 Latin gloss unsourced; F8 mockup badge `12` vs real 25; F9 clitics break the split; F10 mnemonic licensing; F11 curated preview exceeds rankable data; F12 junk rows and feature noise; F13 no core-table migration needed.
