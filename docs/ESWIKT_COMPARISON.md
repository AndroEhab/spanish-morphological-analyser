# ESWIKT COMPARISON — English Wiktionary vs Spanish Wiktionary (kaikki.org extractions)

**Date:** 2026-08-13. **Method:** one streaming pass per dataset, read-only; the existing
`data/morph.sqlite` opened read-only for singleton checks. Companion artifacts:
`recon/eswik_compare.py` (the measuring pass), `recon/eswik_compare.json` (raw counters),
`recon/eswik_problem_words.json` (full entries for the 21 problem words in both datasets).
No pipeline code was changed; no database was rebuilt; nothing was committed. Source files
at repo root are gitignored (`*.jsonl`, `*.jsonl.gz`).

**Executive summary.** The Spanish-edition extraction is **not a replacement** for our
English-edition source and is **only marginally worth merging**. The single decisive fact:
the es.wiktionary extraction carries **zero structured etymology** — no
`etymology_templates` key anywhere in 854,082 entries (English edition: 62,975 entries with
219 template names). Every edge type we depend on (E1 affix, E3 root-key, E5 homograph)
is driven by those templates. The Spanish edition encodes etymology as free prose
("De X y el sufijo -Y", "Del latín X"), which is regular but **unparsed** — building E1
from it means writing a new Spanish-prose parser, and E4/E5 degrade further (569 vs 6,233
derived entries; no `etymology_number`). The Spanish edition's one genuine advantage is
coverage volume — 16,545 conjugated verbs vs 8,783, 99.8% IPA vs 68.5%, 2,801 lemma audio
vs 32 — but it is simultaneously missing things the UI showcases: **zero clitic combined
forms** in `forms[]` (the "With clitics" section would render empty; `hazme`/`hagámoslo`
absent entirely) and 11,455 participle entries with **no lemma link**. The merge that is
realistic is a narrow one: use ES affix-prose to rescue ~800 of our 65,319 singletons
(59.48% → ~58.8%). That is real but small, and the cost (new parser, Spanish glosses,
tag remaps, homograph risk) outweighs it for now. **Recommendation: do not migrate; do not
merge; revisit only if a specific feature (audio, IPA, verb coverage) is prioritized.**

---

## Step 0 — Size, URL, feasibility

| | English edition (current) | Spanish edition (eswiktionary) |
|---|---|---|
| URL | `https://kaikki.org/dictionary/Spanish/kaikki.org-dictionary-Spanish.jsonl` | `https://kaikki.org/eswiktionary/Español/kaikki.org-dictionary-Español.jsonl` |
| postprocessed size | 979 MB (0.96 GiB) | **1,406,458,567 B (1.31 GiB)** |
| entries (lines) | 809,603 | **854,082** |
| distinct words | 771,237 | **838,764** (matches the site's stated figure exactly) |
| extraction date | — | 2026-08-11 (dump 2026-08-04, wiktextract `be32728`) |
| raw (unprocessed) variant | — | `https://kaikki.org/eswiktionary/raw-wiktextract-data.jsonl.gz` (94.7 MB gz) — also lacks templates |

**Feasibility:** 1.31 GiB is under the 2 GB threshold, so the full file was downloaded.
Download time: **7 min 33 s** (curl, ~3.1 MB/s). Both postprocessed and raw variants were
inspected; both lack `etymology_templates`. The site marks the postprocessed format
[DEPRECATED](https://github.com/tatuylonen/wiktextract/issues/1178) but it is the format
our pipeline consumes, so it is the right comparison target.

---

## Step 1 — Structural comparison on the fields our pipeline depends on

All percentages are of the dataset's total entries unless noted. Lemma = entry where not
every sense is a form-of/alt-of sense (pipeline's own `_classify_entry` logic).

### 1.1 Total, distinct words, lemma vs form-of split

| metric | EN (en.wiktionary) | ES (es.wiktionary) |
|---|---|---|
| total entries | 809,603 | 854,082 |
| distinct words | 771,237 | 838,764 |
| lemma entries | 117,253 (14.5%) | 150,588 (17.6%) |
| form-of entries | 691,985 (85.5%) | 703,432 (82.4%) |
| distinct lemma words | 112,401 | 141,701 |
| entries with non-empty `forms[]` | 115,172 | 85,150 (lemma entries with forms: 56.5% vs 81.9%) |

The ES lemma count is inflated: es.wiktionary splits one lexical item into **multiple
entries by sense-group** (`hacer` = 5 verb entries + 1 noun entry; 3,348 `(word,pos)` pairs
have >1 entry vs 1,770 in EN). The pipeline's `etymology_number` disambiguation does not
exist there (0 occurrences) — multi-entry words would need a new merge rule.

### 1.2 `forms[]` coverage — and `hacer` head to head

| metric | EN | ES |
|---|---|---|
| verb lemma words with `forms[]` | 10,751 | 27,163 |
| distinct verb words with ≥10 forms | 8,783 | **16,545** |
| median forms per verb lemma word | 208 | 137 |
| mean forms per verb lemma word | 150 | 85 |
| max forms on one verb | 419 | 274 |
| `hacer` (verb) forms | **303** | **138** |
| — of which voseo (`vos-form`) | 6 | 20 |
| — of which clitic combined (`combined-form`) | **124** | **0** |
| verbs whose `forms[]` include clitic combined forms | 6,725 / 8,783 (76.6%) | **0 / 16,545 (0.0%)** |

**`hacer` forms array shape (ES), verbatim** — same `{form, tags}` shape plus a `raw_tags`
pronoun field; `source` key absent:

```json
[{"form": "haber hecho", "tags": ["impersonal", "infinitive"]},
 {"form": "haciendo",   "tags": ["impersonal", "gerund"]},
 {"form": "habiendo hecho", "tags": ["impersonal", "gerund"]},
 {"form": "hecho",      "tags": ["impersonal", "participle"]},
 {"form": "hago",       "tags": ["first-person", "singular", "indicative", "present"], "raw_tags": ["yo"]},
 {"form": "hacés",      "tags": ["second-person", "singular", "vos-form", "indicative", "present"], "raw_tags": ["vos"]},
 {"form": "hiciera",    "tags": ["first-person", "singular", "subjunctive", "past", "imperfect"], "raw_tags": ["que yo"]},
 {"form": "hizo",       "tags": ["third-person", "singular", "indicative", "present", "perfect"], "raw_tags": ["él, ella, usted"]},
 ... 138 total, 20 voseo forms, 0 clitic combined forms]
```

**Two incompatibilities with our paradigm machinery:**

1. **Tag vocabulary mismatch — preterite is tagged `present`+`perfect`, not `preterite`.**
   `hizo` carries `["indicative","present","perfect"]`. Our 10-slot `_SLOT_PATTERNS`
   require the literal tag `preterite`, so **0 of 17,921** ES conjugated verbs compute a
   paradigm key without a remap; with a mechanical `present+perfect→preterite` remap,
   **17,842/17,921** compute. E2 is salvageable but only with a new tag map.
2. **The infinitive slot is the compound `haber hecho`, not `hacer`.** This shifts every
   residual key: ES `hacer` P=`h`, residual `('aber hecho', …)`; ES `satisfacer` P=``,
   residual `('haber satisfecho', …)` — **different buckets**. In EN both land in the same
   bucket (`'acer','aciendo','ago','aces'`) and `satisfacer` joins `hacer`'s family via E2.
   **From ES data alone, `satisfacer` would not be in `hacer`'s family.** This is a
   regression on a showcased family.

**And the feature that dies outright: clitic combined forms.** The "With clitics" UI
section is built from `forms[]` entries tagged `combined-form`/`object`/`reflexive`
(`app/static/app.js` buckets). ES has **zero** such forms in any verb's `forms[]` — the
section would be empty for every verb. Standalone clitic entries exist (`hacerlo` in ES is
a lemma-style entry glossed "Hacer, con el enclítico lo (pronombre)") but **4,267 of
24,786 have no `form_of` link**, and `hazme`/`hagámoslo` have no entry at all (EN: 133,402
clitic entries, 133,397 linked).

### 1.3 Form-of / inflected-word entries — search-any-form

| metric | EN | ES |
|---|---|---|
| form-of entries | 691,985 | 703,432 |
| entries where any sense has `form_of` | 693,369 | 703,486 |
| lemma-link encoding | `senses[].form_of[].word` + `links` + gloss | **`senses[].form_of[].word` only** (no `links`, no `head_templates`) |
| `mienta` ambiguity | 1 entry, 4 senses (mentar×2, mentir×2) | 1 entry, **5 senses (mentar×2, mentir×3)** — preserved |

The form-of machinery survives: 82.4% of ES entries are inflected forms linked via
`senses[].form_of[].word`, and the `mienta` two-lemma ambiguity case is intact. **But
11,455 ES entries** (pos=verb, `pos_title`="Forma verbal", gloss "Participio de X.") carry
**no `form_of` at all** (`dado`, `hecho` verb forms) — the lemma link exists only inside
the gloss prose ("Participio de dar."). In EN these are structured `form_of: [{"word":
"dar"}]`. A further 33,681 ES entries use the POS value `participle`, which our pipeline
does not know. **The search-any-form feature works, but ~11.5k participle links would need
gloss parsing.**

### 1.4 Etymology — the decisive difference

| metric | EN | ES |
|---|---|---|
| entries with `etymology_templates` | **62,975** | **0** |
| distinct template names | 219 | — |
| entries with etymology text | 66,470 (8.2%) | 91,278 (10.7%) (plain strings, `etymology_texts` list) |
| entries with neither | 743,059 | 762,804 |

**Top-40 template-name histogram (EN only — ES has none):**

```
ety 41466 | der 12441 | cog 7406 | inh 6318 | bor+ 5174 | yesno 5157 | glossary 3194 |
inh+ 3008 | m-g 2018 | lit 1997 | af 1889 | doublet 1774 | bor 1116 | etymon 842 |
es-verb-obj 674 | suffix 627 | surf 623 | uder 607 | dbt 309 | root 267 | lbor 260 |
onomatopoeic 225 | calque 209 | dercat 194 | confix 189 | m+ 181 | wp 176 | unc 169 |
unk 165 | prefix 131 | lg 126 | deverbal 126 | ubor 124 | affix 122 | compound 120 |
cal 105 | slbor 102 | suf 95 | pseudo-loan 90 | ! 87
```

**Is Spanish-internal affixation machine-readable in ES? Not today, but it is regular
prose.** The ES extraction emits `etymology_texts` as plain strings with strongly regular
patterns (all 91,278 etymology-bearing entries classified):

```
De X y el sufijo -Y      19,119   ("De rápido y el sufijo -mente.")
Del latín X              12,611   ("Del latín errare.")
Del ... (other lang)       ~5,000  (griego/inglés/francés/árabe/castellano antiguo/...)
De X y el prefijo Y-       3,509   ("Del prefijo a- y bajo.")
Compuesto de X y Y         1,591   ("Compuesto de qué y hacer.")
OTHER (~10,320)                    (acortamientos, epónimos, "Véase X", mixed)
```

So the *information* our E1 edges need **is present in ES prose** — `rápidamente` =
"De rápido y el sufijo -mente" is exactly the `af|es|rápido|-mente` edge we build from EN
templates. But there is **no structured form**: the E1 parser reads
`etymology_templates[].args`; a Spanish source requires a new prose parser (regex over
`etymology_texts`) plus validation, with no template-level `:bor`/`:inh`/`doublet` markers
to disambiguate borrowed vs inherited — ES `camarero` = "Del latín camararĭus" gives no
way to see that EN records it as a Medieval Latin borrowing with a `doublet` relation.

### 1.5 derived / related / synonyms / antonyms

| metric | EN | ES |
|---|---|---|
| entries with top-level `derived` | 6,233 | **569** |
| entries with top-level `related` | 5,289 | 13,043 |
| sense-level `derived` / `related` | 9,204 / 12,817 | **0 / 0** (everything is top-level) |
| entries with `synonyms` | 104 top + 26,555 sense-level | 26,787 top-level |
| entries with `antonyms` | 140 top + 2,049 sense-level | 3,304 top-level |

**ES `related` is largely semantic, not derivational.** Samples: `katakana→hiragana`,
`domingo→calendario/dominical`, `amigo→amante/barragana/concubino`, `sustantivo→adjetivo/
adverbio/...`, `camarero→barista/mesero/barman`. Only ~4.5% of ES `related` entries carry
an obvious derivational link. EN `related` (`ley→leal/legal/legislar/legítimo/lindo`) is
the derivational signal E4b is built on. **E4/E4b would be nearly dead from ES alone.**
`derived` at 569 entries (1,299 items) vs EN's 6,233 + 9,204 sense-level is a 20–30×
shortfall. ES `compounds` field: 59 entries.

### 1.6 Glosses

| metric | EN | ES |
|---|---|---|
| senses total | 874,006 | 1,035,866 |
| glosses total | 940,971 | 1,031,122 |
| senses per lemma: mean / median / p90 / max | 1.26 / 1 / 2 / 33 | 1.38 / 1 / 2 / 47 |
| gloss language | **English** | **Spanish** |
| register markers | `tags` on senses: 10,621 senses (7.2%): colloquial, vulgar, slang, … | `tags`: colloquial 8,040, derogatory 1,479, vulgar 1,095, outdated 4,288, … |
| region markers | `tags`: Mexico 2,048, Spain 1,458, … (11,054 senses) | `tags`: Chile 3,547, Argentina 2,925, Mexico 2,279, Spain 1,842, Venezuela 2,058, … (richer) |
| domain markers | `raw_glosses` parentheticals | `raw_tags`: Plantas 1,257, Gastronomía 873, Derecho 807, …; `topics` key (`"religion"`) |

ES register/region tagging is **richer and structured** (sense `tags` + `raw_tags` +
`topics`), and there is a per-sense `id`. But every gloss is Spanish — our UI and the
fixture are English. A merge means either English glosses for ES-only words (not
available) or a bilingual UI.

### 1.7 Pronunciation

| metric | EN | ES |
|---|---|---|
| entries with IPA | 167,707 (20.7%) | **853,736 (99.96%)** |
| lemma entries with IPA | 84,447 (68.5%) | **150,335 (99.8%)** |
| lemma entries with audio | 32 (0.025%) | **2,801** (plus 332 form entries) |
| IPA style | phonemic `/…/` + phonetic `[…]` pairs | phonetic `[…]` only (with `raw_tags` accentuation) |

ES IPA coverage is essentially universal and audio is ~87× richer — the single clearest
upgrade in the Spanish edition.

---

## Step 2 — Head-to-head on the problem words

Summary per word (etymology; forms; derived/related; senses). "prose" = `etymology_texts`
plain string; "tpl" = structured templates.

| word | EN edition | ES edition | ES verdict for us |
|---|---|---|---|
| `hacer` | 303 forms (124 clitic), 51 derived, ety tree + `af` | 138 forms (0 clitic), 0 derived, prose "Del castellano antiguo fazer, y este del latín facere…" | **worse** (clitic forms gone, no derived) |
| `gracias` | intj + noun ×2, prose "From gracia < Latin grātia", 0 der/rel (audit: C — related gracia/agradecer exist) | intj + noun; **noun entry is a form-of entry with `form_of:[{word:"gracia"}]`** | **better** (explicit form-of link) |
| `gracia` | 1 noun entry, 5 senses, ety tree, 13 derived + 5 related | 1 noun entry, 21 senses, prose "Del latín gratia…", 0 der/rel | mixed (richer senses, no derived) |
| `camarero` | tpl `bor+ la-med camarārius`; `cámara` derived list **includes camarero** (E4 edge works today) | prose "Del latín camararĭus"; `cámara` has 0 derived → **no camarero↔cámara edge** | **worse** (E4 edge lost) |
| `cámara` | 51 derived | 0 derived, 13 synonyms | worse |
| `ley` | tpl `inh la:lēx/lēgem`; related leal/legal/legislar/legítimo/lindo (audit: C — substring gate) | prose "Del latín lex, a través del acusativo legem."; **0 related** | **no fix** (ES drops the related list entirely) |
| `legal` | tpl `lbor la:lēgālis` + `doublet leal`; related ilegal/legalidad/ley | prose "Del latín lēgālis"; related lícito only | **no fix** |
| `hija` | tpl `inh la:fīlia` | **no etymology at all** (`etymology_texts: ['']`) | worse |
| `hijo` | ety tree, 14 derived, 4 related | long prose, 5 related (vástago/retoño/prole… — semantic) | worse |
| `rápido` | tpl `bor la:rapidus` + doublet raudo, 3 entries | prose "Cultismo. Del latín rapidus…", 2 entries | similar |
| `rápidamente` | tpl `ety :af rápido + -mente` (**already extracted** — the audit's 1,614 adverb gap is mostly non-`-mente` adverbs) | prose "De rápido y el sufijo -mente" | no gain (EN already has it) |
| `mentir` | tpl `inh la:mentīrī` | **no etymology** (`['']`) | worse |
| `mentar` | prose "From mente + -ar." | prose "De mente y el sufijo -ar." | similar (both prose-only) |
| `así` | 22 derived + 2 related (audit: C — adv has no forms) | "Del latín sic."; 0 der/rel | worse |
| `error` | tpl `ety :bor la:error<alt:errōrem>` (junk-killed today); related errar (audit: C) | prose "Cultismo. Del latín error."; derived erróneo; **0 related** | **no fix** |
| `errar` | tpl `der la:errāre`; related aberrar/error/erróneo (audit: C — substring gate) | prose "Del latín errare."; 0 der/rel | **no fix** |
| `quehacer` | tpl `ety :af que + hacer` + `univerbation` | prose "Compuesto de qué y hacer." | similar (prose-only) |
| `hechura` | tpl `ety :inh la:factūra` + `doublet factura` | prose "Del castellano antiguo fechura… del latín factura"; 0 doublet | **worse** (doublet link gone) |
| `satisfacer` | 221 forms, E2 paradigm → `hacer` family | 138 forms but **different residual bucket** → E2 edge lost | **worse — family membership lost** |
| `niñe` | tpl `af niña + -e` (audit: C — `-e` in desinence reject list) | **word absent entirely** | **absent** |

**Does ES supply the missing evidence for the audit's declined cases?**

- **`ley`/`legal`** — No. ES `ley` has **no related list** (EN's has leal/legal/legislar/
  legítimo/lindo); ES `legal` relates only `lícito`. The Latin etymons are prose-only.
  Both datasets fail the E4b substring gate; ES has *less* to work with, not more.
- **`error`/`errar`** — No. Same story: ES has 0 related links between them; the Latin
  etymons appear only in prose. The E4b substring gate and junk-ancestor regex failures
  are not rescued by any ES data.
- **The 1,614 no-etymology adverbs** — No. EN's no-etymology adverbs are mostly non-
  `-mente` words (only 57 of 2,608 `-mente` adverbs lack etymology in EN). ES has
  "De X y el sufijo -mente" prose for 1,473 of its 1,561 `-mente` adverbs, but of EN's
  1,827 no-etymology adverb lemmas, only **21** have an ES entry with affix/compound
  prose — and those 21 are mostly spelling variants (`dejuramente`, `impropriamente`).
  Across all POS, ES affix-prose covers **3,590 EN-no-etymology content words** — that
  is the real (and only) E1 harvest, quantified in Step 3/4.

---

## Step 3 — Coverage overlap

| | EN | ES |
|---|---|---|
| distinct words | 771,237 | 838,764 |
| overlap | 467,926 | |
| ES-only words | 370,838 | |
| EN-only words | 303,311 | |
| union distinct words | 1,142,075 | |
| ES-only entries | 372,421 (71,931 lemma entries, 300,490 form entries) | |
| ES-only distinct content lemma words (noun/verb/adj/adv) | 37,468 | |
| — with corpus freq ≥ 1 | 5,461 (14.6%) | |
| — with corpus freq ≥ 10 | 1,300 | |
| EN-only entries | 314,542 (63,089 lemma, 251,453 form) | |
| EN-only distinct content lemma words | 52,309 (16,509 with freq ≥ 1, 31.6%) | |

**Sample of 30 ES-only words** (deterministic stride, then characterized): 24/30 are
inflected forms of verbs the EN edition never indexed (`achajuanémonos`, `agarrafara`,
`aproarías`, `botanearán`, `cerrajeareis`, `desolazaste`, `empollerásemos`,
`ezquerdearais`, `jardineáremos`, `manferisteis`, …); the 6 lemma entries are `-achuela`
(suffix), `Goyret` (surname), `Región de Coquimbo` (place phrase), `dementofobia` (rare
compound), `encrudeciendo` (gerund-as-lemma), `no pasar naranja` (phrase). **Mostly
regional/rare verbs and proper names — not everyday lemmas.**

**The 5,461 ES-only content lemmas with real corpus frequency are dominated by proper
names and orthographic variants**, not new Spanish vocabulary: `sam, nick, kelly, laura,
doc, karen, sara, stan, juan, eva, rusia, charlotte, tio, mia, miami, sera, diego,
todavia, collins, bang, paula, teresa, manhattan, aca, miranda, finn, ningun, escocia,
yang, ai, facebook…` (`tio`="Grafía obsoleta de tío", `todavia`="Grafía alternativa de
todavía", `aca`=Quechua loanword "excrement", `sera`="cesta de esparto" — real but obscure;
the capitalized ones are names). 2,750 ES-only lemma words (3.9%) are accent/orthography
variants of words we already fold-match.

**Sample of 30 EN-only words**: 24/30 are **clitic combined forms** (`alójalas`,
`arrendarte`, `avivándolo`, `cablearla`, `concentrándoos`, `desosegarte`,
`finiquitándoles`, `incursionándote`, `segarme`, …) that ES does not generate; the 6 lemma
entries are `&` (conjunction), `acelular`, `chifurnia`, `dáctilo`, `guerra electrónica`,
`otorgable`, `pinnulado` — real content words. **EN-only is mostly the clitic gap; ES-only
is mostly verb-form noise + names.**

**Would a union add real lemma coverage?** A union would add ~90,025 lemma words
(141,701 ∪ 112,401 − 112,401), but of the 37,468 ES-only content lemmas, 85% have zero
corpus frequency and the high-frequency share is names and spelling variants. Real new
*common* lemmas are maybe a few hundred to ~1–2 thousand (obscure nouns/verbs like
`dementofobia`, `aca`). The union's main value is not coverage — it is ES's **prose
etymology** for words we already have but lack evidence for (next section).

---

## Step 4 — The verdict

### (a) Strictly better, worse, or complementary?

**Complementary with a heavy lean toward "worse for our specific machinery".** ES wins on:
conjugated-verb inventory (16,545 vs 8,783), IPA (99.8% vs 68.5%), audio (2,801 vs 32
lemma entries), register/region tagging, form-of volume (703k vs 692k), and the
`mienta`-style ambiguity encoding. ES loses on everything the family algorithm is built
on: structured etymology (0 templates), derived lists (569 vs 6,233+), derivational
`related` (ES's is semantic), clitic combined forms (0 in `forms[]`; the UI's "With
clitics" section dies), `hacer`'s paradigm family (`satisfacer` drops out), `hechura`'s
doublet link, `ley`/`legal` and `error`/`errar` evidence, `niñe` (absent), and 11,455
participle links (gloss-prose only). It is **not a swap-in replacement** — it is a
secondary evidence source.

### (b) Could the family algorithm be built from it?

| edge | from ES alone | what breaks |
|---|---|---|
| E1 affix | **possible but requires a new parser** | 19,119 "De X y el sufijo -Y" + 3,509 "…prefijo Y-" + 1,591 "Compuesto de X y Y" prose patterns; no `af`/`suffix`/`prefix` templates, no `:bor`/`:inh`/`doublet` markers, no `surf`/`deverbal`/`prothetic` typed templates |
| E2 paradigm | possible after tag remap | preterite tagged `present`+`perfect` (0 keys without remap); infinitive slot is `haber X` → residual keys shift → `satisfacer`≠`hacer` bucket |
| E3 root-key | only via prose parsing | "Del latín X" (12,611) is parseable but untyped; no inherited/borrowed mode, no PIE tree |
| E4 derived | **dead** | 569 entries (1,299 items) vs EN 6,233 + 9,204; no sense-level |
| E4b related | dangerous | ES `related` is mostly semantic (hiragana, amante) — E4b's gates would reject most, but the signal is absent |
| E5 homograph | **dangerous** | no `etymology_number`; every same-word multi-POS entry (3,348 pairs) would need a new merge rule to avoid cross-POS conflation |

Buildable only after: a Spanish-prose etymology parser (+ tests), a preterite tag remap,
an impersonal-slot filter for paradigm keys, a `participle`-POS mapping, gender extraction
from `pos_title` (no `head_templates`), and an entry-merge rule for sense-group splits.
Estimated 2–4 dev-days for the parser alone, before any quality validation. **Not
buildable with the current pipeline as-is.**

### (c) Is there a realistic merge strategy? Effort and expected singleton gain

**Yes, a narrow one: en.wiktionary as backbone + ES prose etymology as an E1 gap-filler.**

Measured harvest (the only substantial E1 opportunity):
- ES affix/compound prose ∩ EN-no-etymology content words: **3,590** (EN has no etymology
  at all for these).
- Of those, **2,757 are current DB singletons** (of 65,319).
- After E1 gates (affix in the pipeline's closed inventory, 4-char allomorph overlap):
  **~805 pass** (1,170 pass the affix-inventory check; the allomorph gate cuts further).

Effect on the singleton rate (69,745 / 117,253 = **59.48%** today, matching the audit's
recent build):

| scenario | singleton rate |
|---|---|
| current DB (audit's 66.2% was an earlier build; DB rebuilt since) | 59.48% |
| + 805 E1 merges from ES prose | ~58.8% |
| + all 1,170 affix-inventory candidates | ~58.5% |
| + all 2,757 (unrealistic, gates would reject most) | ~57.1% |
| audit's projections on its 66.2% baseline: bug-only fixes ≈62%, all-C fixes ≈57.4% | — |

So ES-prose E1 adds roughly **0.7–1.0 percentage points of singleton reduction** on top of
what EN-only extraction fixes can already achieve (~59.5% → ~57.4%). It does **not** move
the needle on the 92% of singletons in the `0<freq<1`/`freq==0` bands, where the audit
found the C-rate is 13%/7% — ES prose helps the same low-frequency tail. The
`ley`/`legal`, `error`/`errar`, and adverb cases stay unfixed (Step 2).

Effort for the merge: (1) ES prose parser for the three regular patterns, ~1–2 days;
(2) only the ES fields needed (`word`, `pos`, `etymology_texts`) → a ~300 MB derived
JSONL or a SQLite side table, since the full 1.31 GiB re-parse is unnecessary; (3) an
E1-adjacent loader consuming prose edges with the existing gates (they already run on
prose `from`/`variant` kinds, so the machinery exists); (4) gate validation on the ~800
candidates (J2 compound rule, Latin-provenance filter). Total realistic effort: **2–3
dev-days** for a 0.7–1.0pp gain. That is a defensible small project, not a migration.

### (d) What it would COST

- **Build time:** ES file is 1.43× the EN file; a full ES build reuses the same passes.
  EN build is ~2 min; ES alone ~2.5–3 min; a merged two-file build ~3–4 min. The 47 s
  streaming analysis (both files) is not the bottleneck; the SQLite load is.
- **DB size:** current 300.8 MB. Merging both lemma tables (~202k lemma words vs 112k)
  and the ES forms array (27k conjugated verbs, median 137 forms) adds roughly
  **+30–50% (~400–450 MB)**; the ES-only form entries (703k) duplicate the EN form table
  for the 468k overlapping words and would need a dedup key.
- **Glosses:** ES glosses are Spanish; our UI, fixture, and reverse-lookup are English.
  Every ES-only lemma would show a Spanish gloss (or nothing), and ~90k new lemma rows
  would need a `lang` marker or a bilingual UI. This is the largest user-visible cost.
- **Code risk:** new tag remaps (preterite, participle), new entry-merge rule for
  sense-group splits (3,348 multi-entry words), gender from `pos_title`, E5 without
  `etymology_number`. Each is small; together they touch every pipeline stage
  (`extract.py`, `paradigm.py`, `family.py`, `build.py`).

### (e) One recommended action

**Do not migrate; do not merge now.** Keep the English edition as the sole backbone. The
Spanish edition is not a replacement (no structured etymology, no clitic forms, no derived
lists, `satisfacer` leaves `hacer`'s family) and its only material merge gain — ~800
singletons rescued via prose-affix parsing, 59.5% → ~58.8% — is small relative to the
cost and to the ~57.4% ceiling EN-only extraction fixes already reach. If the product
later prioritizes **audio or IPA** (the ES edition's unambiguous wins), re-download the
1.31 GiB file and import only `sounds`/`etymology_texts` into the existing DB as a
secondary table — that can be done without touching the family algorithm at all. If the
singleton rate must move further after the EN extraction fixes are exhausted, the ES
prose-affix harvest (~805 edges) is the cheapest remaining lever, but it is a 2–3
dev-day project with a sub-one-point payoff. **Verdict: not worth it today.**

---

## Reproducibility

- `recon/eswik_compare.py` — streams both JSONL files once each, emits
  `recon/eswik_compare.json` + `recon/eswik_problem_words.json`.
- Full-file scans for paradigm keys, clitic counts, adverb etymologies, singleton gates:
  one-off scripts in this session (queries documented inline in the report where the
  number matters; the two JSON artifacts above carry the raw counters).
- `data/morph.sqlite` opened read-only for singleton/frequency checks (69,745 singleton
  lemmas / 117,253 = 59.48%).
- Download: `curl -o kaikki.org-dictionary-Español.jsonl "https://kaikki.org/eswiktionary/Espa%C3%B1ol/kaikki.org-dictionary-Espa%C3%B1ol.jsonl"` (7 min 33 s).
