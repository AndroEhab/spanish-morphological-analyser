# Cognados en inglés — Feasibility & Precision Study

**Date:** 2026-08-14. **Scope:** measurement only. No application, pipeline, or test
file was changed; nothing was committed. Read-only queries against
`data/morph.sqlite` (2026-08-14 build, 117,253 lemmas) and one streaming pass over
the English kaikki edition. Companion artifacts under `recon/cognates/` (gitignored):
`measure_english.py` (the streaming pass), `join_measure.py` (the three joins),
`en_latin.jsonl` (English lemmas citing Latin, 38.4 MB), `en_counts.json`,
`probe_entries.json` (raw etymology records for the 12 probe words),
`join_output.json` (per-lemma cards, sensitivity table, audit samples, adversarial
cards). Method follows the house conventions (SINGLETON_AUDIT.md / ESWIKT_COMPARISON.md:
streaming pass, seeded audit, numbers marked **[measured]**).

---

## Step 1 — The English data

URL discovered from kaikki.org (the dictionary index page lists one file):

```
https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl
```

(The plan's 2.9 GB figure came from that same URL.) A gzipped variant exists
(`...jsonl.gz`, 502 MB) but the postprocessed plain format is what our pipeline
consumes, so the plain file was downloaded.

| fact | value [measured] |
|---|---|
| size on disk | 3,212,295,539 bytes (3.21 GB / 2.99 GiB) |
| download time | 998.7 s (~16.6 min, ~3.2 MB/s curl) |
| gitignore | `*.jsonl` already present; `git check-ignore` confirms the file is ignored |
| last entry verified | valid JSON (`Elon Musk`, name) |
| streaming pass time | 53.8 s (first pass, unfiltered) / 46.8 s (with the join filter) |

---

## Step 2 — The English side (one streaming pass)

All counts are over English **lemma entries** (not form-of entries), classified with
the pipeline's own `_classify_entry`.

| metric | value [measured] |
|---|---|
| total entries | 1,487,639 |
| lemma entries | 804,198 (54.1%) |
| lemma entries with `etymology_templates` | 462,365 |
| lemma entries citing a `la*` code in any template | 38,014 |
| — citing via the pipeline's etymon vocabulary (inh/bor/der/ety/etymon/root + tree rows) | 32,226 |
| — citing `la*` via `cog`/`m+`/calque/affix templates only (not joined) | ~5,800 |
| legacy-only (`etyl`/`lena`) entries | 0 |
| distinct Latin norms cited (post junk-filter) | 21,252 |
| distinct Latin norm_roots (prefix-stripped) | 18,839 |
| distinct Latin root keys (first5/first4 + supine) | 11,199 |
| English words in the join index (deduped by word) | 30,201 (38,096 lemma-entry records) |

**Latin-family codes cited** (template args): `la` 33,355 · `la-lat` 3,140 ·
`la-med` 2,731 · `la-new` 1,485 · `la-vul` 834 · `la-ecc` 146 · `la-cla` 125 ·
`la-eme` 56. The task's six codes all appear; `la-cla`/`la-eme` are the only extras.

**Template names carrying a `la*` citation** (top): `der` 20,961 · `uder` 5,835 ·
`bor` 5,704 · `cog` 2,114 · `bor+` 2,042 · `lbor` 1,244 · `af` 767 · `m+` 230 ·
`calque` 215 · `suf` 197 · `ubor` 183 · `suffix` 170 · `dercat` 97 · `prefix` 70 ·
`der+` 67 · `inh` 6. The join uses the same etymon vocabulary the Spanish side was
built from (cog/m+/calque are `_IGNORE_TEMPLATES` there too).

**Fan-out of Latin norms over English words:** almost entirely small — 13,690 norms
cited by exactly 1 English word, 4,943 by 2, 1,579 by 3; max post-filter fan-out is
26 (`caput`). Norm_roots max 31; root keys max 102 (`creT`). **No English-side
fan-out cap is needed**: the sensitivity table (below) is identical for
raw / cap-200 / cap-400 / cap-1000.

**Junk norms removed by the filter (both sides):** `is_usable_ancestor` (pipeline's
own rule) + pure-lowercase-ASCII ≥3 chars + an observed language-code leak set
(`grc, peo, ar, akk, gkm, hin, qed, auc, ett`). This removes `-` (cited by **1,529**
English words — a single-hyphen template arg), `ex-`/`dis-`/`ad-`-style prefix
fragments, `testudin-`-style reconstructed stems, `me(n)sa`, `pila#pillar-pier-latin`,
`cf.`, `viꝫ`, etc. The same filter is applied to our etymon table before joining.

**Raw etymology records for the 12 probe words** (verbatim, `la*`-relevant
templates; full records in `recon/cognates/probe_entries.json`):

```
fable (noun/verb):
  {root|en|ine-pro|*bʰeh₂-|speak}
  {inh|en|enm|-}  {der|en|fro|fable}
  {der|en|la|fābula}          → norm fabula
  {doublet|en|fabula}

fabulous (adj):
  {etymon|en|:inh|enm:fabulous<ety:der<la:fābulōsus>>|1}
  {inh|en|enm|fabulous}
  {der|en|la|fābulōsus|celebrated in fable}   → norm fabulosus
  {suf|en|fable|ous}

affable (adj):
  {bor+|en|fr|affable}
  {der|en|la|affābilis}       → norm affabilis
  {surf|en|af-|fable}

confabulate (verb):
  {root|en|ine-pro|*bʰeh₂-|speak}  {etydate|1623}
  {bor+|en|la|cōnfābulātus|1}      → norm confabulatus
  {glossary|perfect}{glossary|active}{glossary|participle}
  {af|en|-ate|verb|verb-forming suffix}

project (noun/verb):
  {ety|en|:bor|la:prōiectus}  {bor|en|la|prōiectus}   → norm proiectus
inject (verb):
  {root|en|ine-pro|*(H)yeh₁-}
  {der|en|la|iniectus|iniectus, injectus}             → norm iniectus
subject (adj/noun/verb):
  {der|en|la|subiectus||…lying under…}                → norm subiectus
  {der|en|la-med|subiectō}                            → norm subiecto
object (noun/verb):
  {ety|en|thing|:bor|fro:object<ety:inh<la-med:obiectum>>|1}
  {der|en|la-med|obiectum||object}                    → norm obiectum
  {prefix|en|ob|against|ject}
abject (adj/noun):
  {der|en|la|abiectus|abandoned; cast aside}          → norm abiectus
conduct (noun/verb):
  {der|en|la-lat|conductus|defense, escort}           → norm conductus
  {der|en|la|conductus}
produce (verb):
  {etymon|en|:inh|enm:produce<ety:der<la:prōdūcō>>|1}
  {der|en|la|prōdūcō|to lead forth}                   → norm produco
reduce (verb):
  {der|en|la|redūcō||reduce}                          → norm reduco
```

Note for the mockup question: `fable/fabulous/affable/confabulate` cite
`fabula/fabulosus/affabilis/confabulatus`; our `hablar` cites `fabulor/fābulārī`
(plan §B2 confirmed verbatim — none of the four norms appears in hablar's chain).

---

## Step 3 — The three joins

### Common machinery (identical on both sides)

- **Our side:** the `etymon` table's `la*` rows only (20,396 lemmas). Each norm
  passes the junk filter; `norm_root` = one Latin prefix stripped (the build's
  `_strip_latin_prefix`, remainder ≥3 chars); root keys = `_latin_root_keys`
  (strip one prefix; `first5`, or `first4` when 4–5 chars; plus `first3+"T"` when
  the stripped form matches the verb/nominal shape regexes).
- **English side:** the same three key types computed identically from the same
  pipeline functions, so norms are byte-identical across the join.
- **Spanish-side fan-out cap:** 60 (the shipped cousins `_COUSIN_FANOUT_CAP`).
  Keys cited by >60 Spanish lemmas are dropped: norms `mens` (2,537), `sub` (242),
  `super` (104), `ante` (64), `inter` (63); norm_roots additionally `ter` (70);
  root keys additionally 37 supine keys (`tenT` 139, `venT` 120, `creT` 108,
  `facT` 99, …). Without this cap, `mens` alone would flood every `-mente` adverb.
- **English-side fan-out cap:** none needed — max norm fan-out 26, max key fan-out
  102 (post-filter); caps at 200/400/1000 change nothing (measured).

### (a) — Exact `norm` join

Rule: our lemma's `la*` norm = English word's `la*` norm. Zero new inference; this
is the cousins' strongest signal verbatim.

| metric | value [measured] |
|---|---|
| lemmas with ≥1 English cognate | **13,651 / 117,253 = 11.64%** (66.9% of the 20,396 Latin-etymon lemmas) |
| pairs | 43,330 |
| mean / median / max cognates per covered lemma | 3.17 / 2 / 34 |
| precision (40-pair audit, strict correct) | **34/40 = 85.0%** |
| precision (correct + arguable) | 38/40 = 95.0% |
| fan-out cap needed | Spanish side 60 (as shipped); English side none |

Weak classes: 1,098 pairs (2.5%) join through a bare Latin preposition/prefix norm
(`trans` 220, `ante` 308, `contra` 154, `post` 182, `extra` 48, `pro` 90, …) —
shared prefix, not shared root (audit #1). Homograph norms (`salio` leap vs `salio`
salt — audit #26) are rare (1/40).

### (b) — `norm_root` join (the cousins fallback, measured alone)

Rule: our lemma's `norm_root` = English word's `norm_root` (one Latin prefix
stripped on each side). This is exactly the key that powers the cousins strip.
Every (a) pair is also a (b) pair (same norm ⇒ same stripped norm on both sides),
so (b) is the superset join.

| metric | value [measured] |
|---|---|
| lemmas with ≥1 English cognate | **14,393 / 117,253 = 12.28%** (70.6% of Latin-etymon lemmas) |
| pairs | 61,204 |
| mean / median / max cognates per covered lemma | 4.25 / 3 / 41 |
| precision (40-pair audit, strict correct) | **35/40 = 87.5%** |
| precision (correct + arguable) | 38/40 = 95.0% |
| fan-out cap needed | Spanish side 60; English side none |

Recovers the prefixed-reflex pairs the exact join misses (`objetar` ↔ `jetty` via
`iectare`, `sujetar` ↔ `subject` via `subiectus`/`subiecto`). Weak class: the
`tra` collision — `intra`/`contra`/`extra` all strip to `tra`, producing 520 pairs
(0.85%) that are cross-preposition false joins (audit #33, #34).

### (c) — Root-key join (the mockup's join, designed explicitly)

Rule (every rule stated):
1. Take each side's `la*` norms through the junk filter.
2. Strip at most one Latin prefix (`_LATIN_PREFIXES`, remainder ≥3 chars).
3. Key = `first5` of the stripped form (`first4` when 4–5 chars) **plus** the
   **supine bridge**: `first3+"T"` whenever the stripped form matches the
   pipeline's verb/nominal shape regexes (`…re|o|io|are|ere|ire|ari|iri`,
   `…ndus|tura|tus|tum|tor|tio|bilis|men|mentum|trix`).
4. Join on any shared key; Spanish-side cap 60; English-side none.
5. Deliberately **no** stem truncation (E3-rejected at ~60% precision in the
   family work) and **no** compositional vowel weakening (`conficere`-type `a→e`
   is not bridged); the `obiectāre→iectāre` cases are covered by rule 2.

The supine bridge is what reaches `affabilis → fabilis → fabT` (the mockup's
fourth word) — and it is also where most of the errors live.

| metric | value [measured] |
|---|---|
| lemmas with ≥1 English cognate | **16,494 / 117,253 = 14.07%** (80.9% of Latin-etymon lemmas) |
| pairs | 239,008 |
| mean / median / max cognates per covered lemma | 14.49 / 8 / 110 |
| precision (40-pair audit, strict correct) | **28/40 = 70.0%** |
| precision (correct + arguable) | 29/40 = 72.5% |
| fan-out cap needed | Spanish side 60 (drops 37 supine keys); English side none |

**Sensitivity: the E3 `first4` gate does not rescue (c).** Applying the family
builder's first4-overlap gate to the same 40 samples gives 24/27 = 88.9% strict on
the surviving 67.5% of pairs — but it kills **correct** pairs too: `delator ↔
Oblation` (`lato` vs `latu`, both from `ferre`), `coproducir ↔ productive` (`duco`
vs `duct` — the whole `-duc-` family), `estrujar ↔ -tort` (`torquere`/`tortus`),
`aguzar ↔ acuate` (`acuere`/`acutus`); it still misses `callejero ↔ Calliope`
(`callis`/`calliope`, both first4 `call`) and `terrorista ↔ subterrene`
(`terrere`/`terra`, both first4 `terr`); and it drops **affable** (`fabilis`
first4 `fabi` vs `fabul-` first4 `fabul`). The gate was tuned for Spanish–Spanish
inherited edges, where both sides show the same citation morphology; English
borrowings systematically cite perfect participles (`ductus`, `tortus`) that the
gate cannot bridge. Not a viable gate here.

### Error classes in (c), with the audit's concrete instances

1. **Supine-key collisions** — the `first3+"T"` bridge merges roots that share a
   first3 but diverge at position 4+: `hablar ↔ forge/forgery/fabricate/
   fabrication/fabrefaction/fabricable` (fari vs faber, via `fabT`),
   `poner ↔ Pontus` (pono vs pontus, via `ponT` — the E3 textbook case),
   `carecer ↔ carrion` (careo vs caro, via `carT`), `reformar ↔ fornicator`
   (forma vs fornix, via `forT`), `asunceno ↔ assimilation` (sumo vs similis,
   via `assT`), `acecho ↔ assimilable` (sequi vs similis, via `assT`),
   `hundimiento ↔ funest` (fundere vs funus, via `funT`), `remanecer ↔
   manumissive` (manere vs manus+mittere, via `manT`), `pando ↔ Pantocrator`
   (pandus vs pantocrator, via `panT` from the `-ndus`/`-tor` shapes).
2. **False prefix strips** — the closed prefix list applied unconditionally
   carves real words into non-words that collide: `sedens → dens` collides with
   `dens` (tooth), flooding `sentar`'s card with the whole tooth family;
   `dentitio → ntitio` collides with `sentio → ntio` (`sentir ↔ dentition/
   denticulate`); `intra/contra/extra → tra` (also in (b)).
3. **First5 collisions on short stems** — real words sharing a 5-char prefix:
   `terreo`/`terrenus` (`terrorista ↔ subterrene`), `mentha`/`mentalis`
   (`mental ↔ mint`), `callis`/`calliope` (`callejero ↔ Calliope`),
   `canthus`/`kantharos` (`decantar ↔ cantharus`, uncertain Greek roots).

### The adversarial cases the task specified

- **`mensa` (table) / `mensis` (month) / `mens` (mind): no cross-conflation.**
  The first5 keys keep them apart: `mesa` (norms `mensa, mesa, metior`) gets
  `Mensa, amensal, commensal, mensa, mesa, mese, mess`; `mes` gets only `menses`;
  `mental` gets the mind set (`dement, mental, mens rea, menticide, …`) but never
  a table/month word. The feared table↔month↔mind merge **does not happen** under
  first5 keys — it happens only under a ≥3-char prefix scheme, which (c) does not
  use. The residual errors inside `mental`'s card are intramural homographs
  (`mint` < mentha, `mentagra` < mentum, via the `menta` first5) and the deep
  `comment` family (via `commentari → mentari`, arguable).
- **`sentir` / `sentar`: they do not conflate with each other** (`sentio → ntiT`
  vs `sedentare → denT`), but `sentar` is the single worst card in the join:
  its `se`-strip (`sedens → dens`) and `de`-strip (`sedentare → dentare → denT`)
  dump 22 of the 23 tooth-family words (`dent, denture, indent, dentine,
  canine tooth, mesiodens, …`) onto it; only `sedentary` is right.
- **`ducere` descendants: rich and correct.** All eight `-ducir` lemmas share the
  `-duc-` set (66 English words each: `conduct, produce, reduce, induce, deduce,
  seduce, traduce, subdue, ducat, duchy, condottiere, …`) — genuinely the same
  root. This is the flagship "rich correct card" case (and one the first4 gate
  would destroy).

---

## Step 4 — Verdict

| join | coverage | mean per covered | precision (strict) | precision (+arguable) | ships? |
|---|---|---|---|---|---|
| (a) exact `norm` | 11.64% | 3.17 | **85.0%** (34/40) | 95.0% | at the bar, knife-edge |
| (b) `norm_root` | 12.28% | 4.25 | **87.5%** (35/40) | 95.0% | **yes — the recommendation** |
| (c) root keys | 14.07% | 14.49 | **70.0%** (28/40) | 72.5% | **no** |

**Recommendation: ship (b)** — the exact-norm join with the cousins' own
`norm_root` fallback, both already house semantics (it is the same pair of keys the
cousins strip uses, with the same 60-cap). It clears the project's ≥85% bar
(87.5% strict, 95.0% lenient; n=40 ⇒ ±~10% sampling uncertainty, so "at or just
above the bar" is the honest reading), it subsumes (a) entirely, and it covers
12.28% of lemmas. The card shows the §52 empty state ("No useful English root
relatives found.") for ~88% of words — sparse-but-correct is the legitimate,
spec-blessed outcome, and far better than a rich wrong one.

**The mockup set is NOT reachable by the recommended option.** `hablar` receives
**zero** English cognates under (a) and (b) — the four mockup words cite
`fabula/fabulosus/affabilis/confabulatus`, none of which appears in hablar's chain.
Only the root-key join (c) produces fable/fabulous/affable/confabulate (all four,
verified), and (c) fails precision at 70.0% — it would also put `forge, forgery,
fabricate, fabrication` (the faber family, not fabula) on hablar's card. The owner
should know: **the mockup promises a set the measured data delivers only through a
join that fails the project's precision bar.** Shipping (b) means hablar shows the
empty state and the mockup's exact card cannot be reproduced without accepting a
(c)-class join at ~70% precision, which §51/§52 and the F5 gate forbid.

Secondary findings the owner may want on record:

- **The English-side caps are a non-issue** — after the junk filter, no English
  norm/key exceeds 102 words; the sensitivity table is flat across raw/200/400/1000.
- **English-side POS hygiene matters at ship time:** 749 index entries (2.0%) are
  bound morphemes/phrases (`-fix`, `post-`, `-form`, `vagina dentata`, `canine
  tooth`); 235 of them form (b)/(c) pairs. Excluding `suffix/prefix/phrase/…` POS
  (the pipeline's `_BOUND_POS`) is a cheap refinement that only improves the card.
- **Homograph gloss mismatch:** the English index merges POS entries of one word
  (`peel` = skin-verb < `pilare` and shovel-noun < `pala`); the card shows the
  first sense's gloss, which can name the wrong sense for the root that matched.
- **The `-mente` adverbs:** `mens` (2,537 lemmas) is capped out of all three
  joins, so no `-mente` adverb gets English cognates — a large, correct-looking
  mass (mental, demented, …) is deliberately withheld because the cap cannot
  distinguish them. This is the cousins cap behaving exactly as designed.

---

## Appendix — the three 40-item audits, verbatim

Judged pairs are the seeded samples (`random.Random(42)`, 40 uniform pairs per join from the covered-pair population of the shipped-shape join: ES cap 60 / EN cap 400). **Strict precision = ✔/40; lenient = (✔+◑)/40.** Connecting key shown is the shared key set on the Spanish side.

### (a) exact-norm join

| # | Spanish (pos) | English — gloss | shared keys | verdict | reason |
|---|---|---|---|---|---|
| 1 | transponer (verb) | tralineate — To deviate; to stray; to wander. | pono,trans | ✘ wrong | shared prefix only (trans in transponer vs trans+linea in tralineate) — not a root cognate |
| 2 | viajante (adj) | viaticum — The Eucharist, when given to a person who … | via,viaticum,viaticus | ✔ correct | both from via (road) |
| 3 | feral (adj) | ferous — wild; savage; feral | feralis,ferus | ✔ correct | both from ferus (wild) |
| 4 | código (noun) | caudical — Relating to the caudex. | caudex | ✔ correct | codex and caudex are variant forms of the same Latin word |
| 5 | hacer (noun) | omnific — Capable of making or doing anything; all-c… | facere,facio | ✔ correct | hacer < facere; omnific = omni + facere |
| 6 | multicanal (adj) | cannoneer — An artillery soldier who maintains and ope… | canalis,canna | ◑ arguable | canalis is derived from canna — indirect but real |
| 7 | soberanismo (noun) | sovereignty — The quality or state of being sovereign. | superanus | ✔ correct | both from superanus |
| 8 | inmaculadamente (adv) | macula — An oval yellow spot near the center of the… | immaculatus,macula,maculatus | ✔ correct | both from macula (spot) |
| 9 | pos (noun) | post- — after; later. | post | ✔ correct | both from post — weak but real |
| 10 | capaz (adj) | captor — One who is holding a captive or captives. | capio | ✔ correct | capaz < capax < capere; captor < capere |
| 11 | amochiguar (verb) | multeity — manifoldness; multiplicity; the quality of… | multus | ✔ correct | amochiguar's chain cites multus (multificare); multeity < multus |
| 12 | atrevido (adj) | tribe — An ethnic group larger than a band or clan… | tribus | ◑ arguable | atrevido's chain reaches tribus (atrever < attribuere < tribuere < tribus); deep, semantically opaque |
| 13 | revolver (verb) | revolt — To rebel, particularly against authority. | revolvere,revolvo | ✔ correct | both from revolvere < volvere |
| 14 | luminaria (noun) | lumirubin — A structural isomer of bilirubin, formed d… | lumen | ✔ correct | both from lumen (light) |
| 15 | prescribir (verb) | shrive — To hear or receive a confession (of sins e… | praescribere,scribo | ✔ correct | prescribir < praescribere < scribere; shrive is the Germanic twin of scribe |
| 16 | capear (verb) | chapiter — Obsolete form of chapter. | capitulum,cappa,caput | ✔ correct | capear's ES etymology tree derives cappa < capitulum < caput (standard cappa<caput account); chapiter < capitulum |
| 17 | enfrente (adv) | front — The foremost side of something or the end … | frons | ✔ correct | both from frons (forehead/front) |
| 18 | campanero (noun) | campaniform — In the shape of a bell. | campana | ✔ correct | both from campana (bell) |
| 19 | sociocultural (adj) | portcullis — A gate in the form of a grating which is l… | colo,cultura | ◑ arguable | portcullis < colare (strain, from colum); sociocultural < cultura < colere (cultivate) — colum/colere connection is contested |
| 20 | antipopular (adj) | pueblo — A community in Spain or Spanish America, e… | populus | ✔ correct | both from populus |
| 21 | amable (adj) | Amabel — A female given name from Latin. | amabilis | ✔ correct | both from amabilis < amare |
| 22 | cuellinegro (adj) | col — A dip on a mountain ridge between two peak… | collum,nigrum | ✔ correct | both from collum (neck); col = mountain saddle/neck |
| 23 | agotar (verb) | gt — drop (as a measurement in medical prescrip… | gutta | ✔ correct | agotar < gota < gutta; 'gt' is the prescription abbreviation of gutta |
| 24 | sonrisa (noun) | subrisive — Playful, tongue-in-cheek. | subrideo | ✔ correct | sonrisa < subrideo < ridere; subrisive < subrideo |
| 25 | cuidar (verb) | agitographia — Very fast writing, normally with unintenti… | agito,ago,cogitare,cogito | ✔ correct | cuidar < cogitare < agitare < ago; agitographia < agito < ago |
| 26 | saledizo (adj) | salad — A food consisting principally of raw veget… | salio | ✘ wrong | salio homograph: saledizo < salio (leap); salad cites salio 'to salt' < sal — different verbs |
| 27 | edil (noun) | aedile — An elected official who was responsible fo… | aedilis | ✔ correct | both from aedilis |
| 28 | filoso (adj) | filigree — A delicate and intricate ornamentation mad… | filum | ✔ correct | both from filum (thread) |
| 29 | apostólico (adj) | apostolic — Pertaining to apostles or their practice o… | apostolicus | ✔ correct | same word |
| 30 | insular (noun) | insula — A block of buildings in a Roman town. | insula,insularis | ✔ correct | both from insula (island) |
| 31 | solevar (verb) | levy — To impose (a tax or fine) to collect monie… | levo,sublevare | ✔ correct | both from levare (to raise) |
| 32 | quincena (noun) | December — The twelfth and last month of the Gregoria… | decem,quindecim,quinque | ◑ arguable | quincena < quindecim (quinque + decem); December < decem — real via the decem component, semantically odd |
| 33 | mayor (adj) | major — Greater in dignity, rank, importance, sign… | maior | ✔ correct | both from maior |
| 34 | montuno (adj) | Montagnard — A member of La Montagne (The Mountain), a … | mons | ✔ correct | both from mons (mountain) |
| 35 | junto (adj) | junta — The committee of military officers that ha… | iunctus | ✔ correct | both from iunctus < iungere |
| 36 | repleto (adj) | replete — Abounding, amply provided. | repletus | ✔ correct | same word (repletus) |
| 37 | historia (noun) | historiaster — An inferior historian. | historia | ✔ correct | both from historia |
| 38 | vainilla (noun) | vagina dentata — The mythical toothed vagina; often related… | vagina | ✔ correct | both from vagina (sheath); the EN entry is the phrase 'vagina dentata' |
| 39 | hosco (adj) | fuscin — A brown nitrogenous pigment contained in t… | fuscus | ✔ correct | both from fuscus (dark) |
| 40 | ponderoso (adj) | ponderosa — A pine tree of very large size, native to … | ponderosus | ✔ correct | both from ponderosus < pondus |

**Tally: 34 correct / 4 arguable / 2 wrong — strict 34/40 = 85.0%, lenient 38/40 = 95.0%**

### (b) norm_root join

| # | Spanish (pos) | English — gloss | shared keys | verdict | reason |
|---|---|---|---|---|---|
| 1 | Eurovisión (name) | supervise — To oversee or direct (a task or organizati… | visio,visus | ✔ correct | Eurovisión < visión < visio; supervise < super + videre — both the videre root |
| 2 | imponente (adj) | expone — To expound; to explain. | pono | ✔ correct | imponente < imponere < ponere; expone < exponere < ponere |
| 3 | signo (noun) | signal — A sequence of states representing an encod… | signum | ✔ correct | both from signum |
| 4 | helado (adj) | gelato — An Italian variant of ice cream made from … | gelatus,gelo | ✔ correct | helado < gelare; gelato < gelare |
| 5 | grial (noun) | grail — The Holy Grail. | gradalis | ✔ correct | same word |
| 6 | repago (noun) | pacify — To bring peace to (a place or situation), … | paco,pax | ✔ correct | repago < pagar < pacare < pax; pacify < pacificare < pax |
| 7 | reprensible (adj) | comprehensive — Broadly or completely covering; including … | prehendo,prehensibilis | ✔ correct | both prehendere compounds (reprehendo, comprehendo) |
| 8 | follón (noun) | fals — Medieval copper coin first produced by the… | follis | ◑ arguable | follón (squib) < follis (bellows); fals (coin) < follis (money-bag) — same root, very different senses |
| 9 | margarita (noun) | margaritomancy — Divination by pearls. | margarita | ✔ correct | both from margarita (pearl) |
| 10 | linterna (noun) | lucernal — Of, pertaining to, or using a lamp. | lanterna,lucerna | ✔ correct | linterna < lanterna/lucerna; lucernal < lucerna |
| 11 | morganático (adj) | morganatic — Designating a marriage (or the wife involv… | morganaticus | ✔ correct | same word |
| 12 | abundar (verb) | und — A wave. | abundare,unda,undo | ✔ correct | abundar < abundare < unda; und < unda (wave) |
| 13 | égida (noun) | aegis — A mythological shield associated with the … | aegis | ✔ correct | same word |
| 14 | ciego (noun) | caecum — A cavity open at one end (such as the blin… | caecus | ✔ correct | ciego < caecus (blind); caecum (blind gut) < caecus |
| 15 | bulla (noun) | budge — To move; to be shifted from a fixed positi… | bullio,bullire | ✔ correct | bulla < bullire (boil); budge < OF bouger < VL *bullicare < bullire — verified |
| 16 | fin (noun) | finesse — A skill in the handling or manipulation of… | finis | ✔ correct | both from finis |
| 17 | paletón (noun) | peel — To remove the skin or outer covering of. | pala | ◑ arguable | paletón < pala; 'peel' cites pala — that is the shovel-homograph (peel < pala); the displayed gloss is the skin-peel < pilare: root real, displayed sense wrong |
| 18 | invenir (verb) | inventory — The stock of an item on hand at a particul… | venio,venire | ✔ correct | invenir < invenire < venire; inventory < inventarium < invenire |
| 19 | circunstancialmente (adv) | instantaneous — Occurring, arising, or functioning without… | circum,circus,stans,sto | ✔ correct | circunstancia < circumstare < stare; instantaneous < instare < stare |
| 20 | sustracción (noun) | train — Elongated or trailing portion. | traho | ✔ correct | sustracción < subtrahere < trahere; train < trahere |
| 21 | factor (noun) | benefactor — Somebody who gives a gift, often money to … | factor | ✔ correct | both from factor < facere |
| 22 | cuestión (noun) | question — A worded or expressed sentence, phrase, or… | quaestionem | ✔ correct | both from quaestio |
| 23 | neocapitalismo (noun) | chieftain — A leader of a clan or tribe. | caput | ✔ correct | both from caput (via capitaneus) |
| 24 | encargo (noun) | career — One’s calling in life; one's working occup… | carricare,carrus | ✔ correct | encargo < carricare < carrus; career < carriere < carrus |
| 25 | mismo (adv) | ipsative — Denoting a measure that forces a person to… | ipse | ✔ correct | mismo < ipse; ipsative < ipse |
| 26 | precursor (adj) | recur — Of an event, situation, etc.: to appear or… | curro | ✔ correct | precursor < praecurrere < currere; recur < recurrere < currere |
| 27 | infligir (verb) | profligacy — Careless wastefulness. | fligo | ✔ correct | infligir < infligere < fligere; profligacy < profligare < fligere |
| 28 | impar (adj) | umpire — An official who presides over a sports mat… | par | ✔ correct | impar < impar; umpire < OF nompere < non + par — the 'not-equal one' — verified |
| 29 | caldera (noun) | chowder — A thick, creamy soup or stew. | caldaria,caldus | ✔ correct | caldera < caldaria < caldus; chowder < chaudière < caldaria |
| 30 | inducir (verb) | transduction — The transfer of genetic material from one … | ducere,duco | ✔ correct | inducir < inducere < ducere; transduction < transducere < ducere |
| 31 | hormiga (noun) | formicide — A substance that kills ants | formica | ✔ correct | both from formica (ant) |
| 32 | Bonifacio (name) | Toki Pona — A minimalist constructed language with cre… | bonifatius,bonus,fatum,fatus | ◑ arguable | Toki Pona's 'pona' cites Latin bonus (via Esperanto bona) — literal root, conlang name, useless as a cognate |
| 33 | entrada (noun) | contravallation — A fortification built around a sieged targ… | tra | ✘ wrong | intra → tra vs contra → tra — false strip collision (entrar vs contravallation, different prepositions) |
| 34 | reentrar (verb) | extravagant — Exceeding the bounds of something; roving;… | tra | ✘ wrong | intra → tra vs extra → tra — false strip collision (reentrar vs extravagant) |
| 35 | absceso (noun) | intercessor — One who intercedes, particularly | abscessus,cedo | ✔ correct | both cedere compounds (abscedo, intercedo) |
| 36 | perennizar (verb) | perennate — To survive from one growing season to the … | enno | ✔ correct | both from perennis < per + annus |
| 37 | controversia (noun) | controversal — Facing opposite directions. | tra,troversia,troversus,versus | ✔ correct | same word family (contro + versus) |
| 38 | mocoso (noun) | mucous — Pertaining to mucus. | mucosus,mucus | ✔ correct | mocoso < moco < mucus; mucous < mucosus < mucus |
| 39 | autodescarte (noun) | card — A playing card. | charta | ✔ correct | autodescarte < descartar < carta < charta; card < charta |
| 40 | capataz (noun) | cabochon — A precious stone which has only been polis… | caput | ✔ correct | both from caput |

**Tally: 35 correct / 3 arguable / 2 wrong — strict 35/40 = 87.5%, lenient 38/40 = 95.0%**

### (c) root-key join

| # | Spanish (pos) | English — gloss | shared keys | verdict | reason |
|---|---|---|---|---|---|
| 1 | invocación (noun) | provoke — To cause someone to become annoyed or angr… | vocT,vocat | ✔ correct | invocación < invocare < vocare; provoke < provocare < vocare |
| 2 | emular (verb) | emulous — Ambitious or competitive. | aemT,aemul | ✔ correct | both from aemulari/aemulus |
| 3 | impermeable (adj) | emperor — The male monarch or ruler of an empire. | perT | ✘ wrong | impermeable < impermeabilis < permeare < meare; emperor < imperator < imperare < parare — via perT (im+pero vs im+permeabilis), different roots |
| 4 | pando (adj) | Pantocrator — The ruler of everything, especially as an … | panT,pandu | ✘ wrong | pando < pandus (bent); Pantocrator < Greek pantokrator — via panT from the -ndus/-tor shapes, unrelated |
| 5 | continente (noun) | pertinent — A right that attaches to land, in Scots la… | tinen | ✔ correct | continente < continere < tenere; pertinent < pertinere < tenere |
| 6 | devolver (verb) | devolution — A rolling down. | volT,volve,volvo | ✔ correct | devolver < devolvere < volvere; devolution < devolvere |
| 7 | misterio (noun) | mysterium — Any of various unknown elements thought to… | myste | ✔ correct | same word |
| 8 | sujetar (verb) | project — A planned endeavor, usually with a specifi… | iecT,iecta,iecto | ✔ correct | sujetar < subiectare < iacere; project < proiectare < iacere — the iectare case |
| 9 | souvenir (noun) | advene — To accede or to come to; to be superadded … | venio,venir | ✔ correct | souvenir < subvenire < venire; advene < advenire < venire |
| 10 | fecundidad (noun) | infecundity — Lack of fecundity or fruitfulness | fecT,fecun | ✔ correct | both from fecundus |
| 11 | asunceno (noun) | assimilation — The act of assimilating or the state of be… | assT,assum,sumT,sumo | ✘ wrong | asunceno < assumptio < assumere < sumere; assimilation < assimilare < similis — via assT (assumere vs assimilare), different roots |
| 12 | virtuosamente (adv) | virtue — The idea of all that is good or excellent … | virT,virtu | ✔ correct | both from virtus |
| 13 | cabra (noun) | chevrotain — Any of several small hornless ruminants of… | capra | ✔ correct | cabra < capra; chevrotain < chevrotin < chevre < capra — verified |
| 14 | incidir (verb) | cascade — A waterfall or series of small waterfalls. | cadT,cado,cidT,cider | ✔ correct | incidir < incidere < cadere; cascade < cascata < cadere — verified (shared cado) |
| 15 | hincar (verb) | -fix — Forming nouns denoting a morpheme used in … | figT,figer,figo | ✔ correct | hincar < *figicare < figere; -fix < figere |
| 16 | carecer (verb) | carrion — Rotting flesh of a dead animal or person. | carT,careo | ✘ wrong | carecer < careo (lack); carrion < caro (flesh) — via carT, different roots |
| 17 | reformar (verb) | fornicator — An unmarried person who engages in sexual … | forT,forma,formo | ✘ wrong | reformar < reformare < forma; fornicator < fornicari < fornix — via forT (formare vs fornicari), different roots |
| 18 | delator (noun) | Oblation — The offering of bread and wine at the Euch… | latT,lator | ✔ correct | delator < deferre < ferre; Oblation < oblatio < offerre < ferre |
| 19 | coproducir (verb) | productive — Capable of producing something, especially… | ducT,duco | ✔ correct | coproducir < producere < ducere; productive < productivus < producere |
| 20 | escombro (noun) | cumber — To slow down; to hinder; to burden; to enc… | comT,cumul | ✔ correct | escombro's chain cites cumulus (derived); cumber cites cumulus — same citation |
| 21 | levar (verb) | levy — To impose (a tax or fine) to collect monie… | levT,levar | ✔ correct | both from levare |
| 22 | sociable (adj) | consociate — An associate; an accomplice. | socT,socia | ✔ correct | both from socius/sociare |
| 23 | ambulante (adj) | preamble — A short preliminary statement or remark, e… | ambul | ✔ correct | ambulante < ambulare; preamble < praeambulare < ambulare |
| 24 | callejero (noun) | Calliope — The Muse of eloquence and epic or heroic p… | calli | ✘ wrong | callejero < calle < callis (path); Calliope < Greek kalliope — via calli (first5), unrelated; also a proper name |
| 25 | filamento (noun) | filose — Terminating in a thread-like process, or t… | filT,filam,filo,filum | ✔ correct | both from filum (thread) |
| 26 | batir (verb) | bascule — A counterbalanced structure having one end… | batT,batte,batto | ✔ correct | batir < battuere; bascule < OF bascule < battre + cul < battuere |
| 27 | tieso (adj) | intensive — Done with intensity or to a great degree; … | tensu | ✔ correct | tieso < tensus < tendere; intensive < intendere < tendere |
| 28 | friera (noun) | friable — Easily broken into small fragments, crumbl… | friT,frige,frigi,frigu | ✘ wrong | friera < frigere (cold); friable < friare (crumble) — via friT, different roots |
| 29 | decantar (verb) | cantharus — A large drinking cup with two handles. | canT,canth | ◑ arguable | decantar < ML decanthare < canthus (rim); cantharus < Greek kantharos (cup) — canthus/kantharos relation uncertain |
| 30 | cómodo (adj) | subjunctive mood — Mood expressing an action or state which i… | modus | ✔ correct | cómodo < commodus < modus; 'subjunctive mood' cites modus |
| 31 | terrorista (noun) | subterrene — underground, subterranean | terT,terre | ✘ wrong | terrorista < terrere (frighten); subterrene < subterraneus < terra (earth) — via terre (terreo vs terrenus), different roots |
| 32 | remanecer (verb) | manumissive — Of or relating to manumission (“release fr… | manT,maneo,manes | ✘ wrong | remanecer < remanere < manere; manumissive < manumittere < manus + mittere — via manT, different roots |
| 33 | escamoso (adj) | squame — The scale, or exopodite, of an antenna of … | squam | ✔ correct | escamoso < squama; squame < squama |
| 34 | panizo (noun) | panic — Foxtail millet or Italian millet (Setaria … | panic | ✔ correct | panizo < panicum; panic (millet) < panicum |
| 35 | mediano (adj) | immediate — Happening right away, instantly, with no d… | media | ✔ correct | mediano < medianus < medius; immediate < immediatus < medius |
| 36 | estrujar (verb) | -tort — To make something change its shape. | torT,torcu,troT | ✔ correct | estrujar < *extorciare < torquere; -tort < tortus/torquere |
| 37 | aguzar (verb) | acuate — Sharpened; sharp-pointed. | acuT,acuti,acutu | ✔ correct | aguzar < *acutiare < acutus < acuere; acuate < acutus |
| 38 | acecho (noun) | assimilable — Capable of being assimilated; susceptible … | assT,assec,ctoT,ctor | ✘ wrong | acecho < assectari < sequi (follow); assimilable < assimilare < similis — via assT, different roots |
| 39 | hundimiento (noun) | funest — Causing death or disaster; fatal, catastro… | funT,fundo | ✘ wrong | hundimiento < hundir < fundere (pour/sink); funest < funestus < funus (death) — via funT, different roots |
| 40 | vedeja (noun) | viticetum — A collection of vines. | vitic | ✔ correct | vedeja < viticula < vitis; viticetum < vitis (vine) |

**Tally: 28 correct / 1 arguable / 11 wrong — strict 28/40 = 70.0%, lenient 29/40 = 72.5%**

---

## Post-refinement re-measurement — the shipped join (option b, as implemented)

The three refinements were implemented in `pipeline/english_cognates.py` and
re-measured on the rebuilt database (2026-08-14, second build):

1. **English bound-morpheme/phrase POS excluded** (`suffix`, `prefix`, `phrase`,
   `proverb`, `prep_phrase`, `adv_phrase`, `character`, `punct`, `symbol` — the
   pipeline's own `_BOUND_POS`): `-fix`, `post-`, `vagina dentata` no longer
   enter the card (749 index entries, 2.0%).
2. **Homograph gloss hygiene**: `english_cognate` stores one row per
   (word, cited norm) with the gloss of the entry that cited it, so a merged
   homograph (`peel` the skin-verb < `pilare` vs `peel` the shovel < `pala`)
   displays the sense that actually matched.
3. **Weak classes dropped**: a closed blocklist of Latin preposition/prefix
   words (`trans`, `ante`, `contra`, `post`, `extra`, `intra`, `ultra`,
   `retro`, `circum`, `dis`, `infra`, `pro`, `per`, `prae`, `pre`, `super`,
   `sub`, `inter`, `con`, `com`, `co`, `af`, `ef`, `im`, `sur`, `tra`, `bene`,
   `male`, `satis`, `non`, `semi`, `bi`, `tri`, `quadri`, `multi`, `uni`) is
   applied on both sides of the join. This removes the 1,098 (2.5%)
   prefix-only pairs (`transponer ↔ tralineate` via `trans`) and the 520
   `intra`/`contra`/`extra` → `tra` norm_root collisions (`entrada ↔
   contravallation`), at the cost of a handful of weak-but-real pairs
   (`pos ↔ post-`).

**Shipped join semantics (as built):** for each Latin etymon row of the lemma,
both the exact-`norm` channel and the `norm_root` channel contribute (union,
not strict fallback — the cousins' per-row fallback would have dropped correct
pairs like `conducir ↔ produce/reduce` for lemmas that also have norm
matches); direct-cognate (norm) items sort before shared-latin-root
(norm_root) items, each alphabetically. Caps: Spanish-side fan-out 60
(the cousins `_COUSIN_FANOUT_CAP`), English-side none needed (flat sensitivity).

### Final numbers [measured, on the rebuilt DB]

| metric | value |
|---|---|
| coverage | **14,289 / 117,253 lemmas = 12.19%** (70.1% of the 20,396 Latin-etymon lemmas) |
| pairs | 58,587 |
| mean / median cognates per covered lemma | 4.1 / 2 |
| **precision (fresh 40-pair audit, strict)** | **37/40 = 92.5%** (up from 87.5% pre-refinement) |
| precision (correct + arguable) | 38/40 = 95.0% |
| DB size delta | +4.1 MB (330.4 vs 326.3 MB, +1.26%) |
| build-time delta | +53–68 s (one extra streaming pass; total build ~3.9–5.2 min) |

The two residual wrongs in the fresh audit are both irreducible without
sense-level disambiguation: `embarcadero ↔ Barca` (Latin `barca` the boat vs
the Punic surname `Barca` < `baraq` — homograph norm) and `agenciar ↔
imaginism` (the `im`-prefix strip carves `imago` → `ago`, colliding with
`ago`). Each is ~1/40 = 2.5%; the measured precision already accounts for
them.

### The fresh 40-pair audit, verbatim (shipped union join, seeded sample)

| # | Spanish (kind/key) | English — gloss | verdict | reason |
|---|---|---|---|---|
| 1 | estrechar (norm strictus) | stricture — A rule restricting behaviour or action. | OK | estrechar < strictus < stringere; stricture < strictus |
| 2 | cesación (norm_root cedo) | precession — Precedence. | OK | cesación < cessare < cedere; precession < praecessio < cedere |
| 3 | ignominia (norm ignominia) | ignominy — Great dishonor, shame, or humiliation. | OK | same word (ignominia) |
| 4 | bruma (norm bruma) | brumous — Foggy or misty; wintry. | OK | both from bruma (winter) |
| 5 | distar (norm disto) | dististylus — In mosquitoes, the distal segment of the | OK | distar < disto < stare; dististylus = disti- 'apart' + stylus < disto |
| 6 | apolíneo (norm apollineus) | Apolline — Of or relating to the god Apollo. | OK | both from Apollineus (Apollo) |
| 7 | transformar (norm forma) | platform — A raised stage from which speeches are m | OK | transformar < formare < forma; platform < OF plate-forme < forma |
| 8 | monumento (norm monumentum) | monument — A structure built for commemorative or s | OK | same word (monumentum) |
| 9 | Flegetonte (norm phlegethon) | Phlegethon — A river of fire in Hades. | OK | same name (Phlegethon, river of Hades) |
| 10 | -ífero (norm_root fero) | referrible — referable | OK | -ífero < -fer < ferre; referrible < referre < ferre |
| 11 | producto (norm_root ductus) | redoubt — A small, temporary, military fortificati | OK | producto < productus < ducere; redoubt < reductus < ducere (norm_root ductus) |
| 12 | inescrupuloso (norm scrupulus) | escropulo — A traditional Portuguese unit of mass, e | OK | inescrupuloso < scrupulus; escropulo < scrupulum < scrupulus |
| 13 | cumbre (norm culmen) | culminate — Of a heavenly body, to be at the highest | OK | cumbre < culmen; culminate < culminare < culmen |
| 14 | becada (norm beccus) | beccal — Pertaining to a beak or bill. | OK | becada (woodcock) < beccus (beak); beccal < beccus |
| 15 | obturación (norm obturatio) | obturation — The act of stopping up, or closing, an o | OK | same word (obturatio) |
| 16 | pluviómetro (norm pluvius) | pluviometry — The scientific measurement of rainfall. | OK | both from pluvius |
| 17 | adversario (norm_root versus) | versus — Against; in opposition to. | OK | adversario < adversus < vertere; versus 'against' < vertere |
| 18 | aductor (norm_root duco) | transducer — A device that converts energy from one f | OK | aductor < adducere < ducere; transducer < transducere < ducere |
| 19 | interceder (norm_root cedo) | predecessor — One who precedes; one who has preceded a | OK | interceder < intercedere < cedere; predecessor < decessor < cedere |
| 20 | entendido (norm_root tendere) | pretensive — Pretended; feigned. | OK | entendido < entender < intendere < tendere; pretensive < praetendere |
| 21 | involucro (norm_root volvo) | Volvo — The Volvo Car Corporation, a Swedish man | OK | involucro < involucrum < involvere < volvere; Volvo < volvo 'I roll' |
| 22 | céltico (norm celticus) | Celtic — A branch of the Indo-European languages  | OK | same word (celticus) |
| 23 | servar (norm servus) | serve — An act of putting the ball or shuttlecoc | ? | ? — servar's chain cites servus (servo < servare < servus); serve < servus; the servare/servus link is the accepted *ser- etymology, deep |
| 24 | turbulento (norm turbulentus) | turbulate — To turn (a laminar flow) into a turbulen | OK | both from turbulentus < turba |
| 25 | floreo (norm flos) | floramour — The plant love-lies-bleeding. | OK | floreo < florere < flos; floramour < flos + amor |
| 26 | espátula (norm spatha) | spathe — A large bract that envelops or subtends  | OK | espátula < spatha; spathe < spatha |
| 27 | pie (norm pedem) | piepowder — Chiefly in court of piepowders, etc. (se | OK | pie < pedem < pes; piepowder < OF pied poudreux < pes |
| 28 | introspectivo (norm introspectus) | introspect — To engage in introspection. | OK | both from introspectus < specere |
| 29 | fanático (norm fanum) | fanum — The site of an Ancient Roman temple or s | OK | fanático < fanaticus < fanum; fanum (temple) < fanum |
| 30 | cicerone (norm cicer) | chich — The chickpea. | OK | cicerone < Cicero < cicer (chickpea); chich < cicer |
| 31 | meridiano (norm medius) | medius — The middle finger. | OK | meridiano < meridianus < meridiēs < medius + dies; medius < medius |
| 32 | osario (norm ossarium) | ossarium — An ossuary. | OK | same word (ossarium) |
| 33 | embarcadero (norm barca) | Barca — A surname from Punic, particularly (hist | X | X — embarcadero < barca (boat) < LL barca; Barca (surname) < Punic baraq 'lightning' — homograph norm, different roots |
| 34 | autocontrol (norm rotula) | control — To exercise influence over; to suggest o | OK | autocontrol < control < ML contrarotulus < rotula; control < rotula |
| 35 | son (norm sonus) | sonnet — A fixed verse form of Italian origin con | OK | son < sonus; sonnet < sonetto < son < sonus |
| 36 | proseguir (norm prosequor) | prosecution — The act of prosecuting a scheme or endea | OK | proseguir < prosequi < sequi; prosecution < prosecutio < sequi |
| 37 | salado (norm sal) | sal — Salt. | OK | salado < sal; sal (English entry) < sal |
| 38 | agenciar (norm_root ago) | imaginism — A Russian avant-garde poetic movement, f | X | X — agenciar < ago; imaginism < imago — the 'im' strip carves imago → ago, different roots |
| 39 | comerciable (norm commercium) | commerce — The exchange or buying and selling of co | OK | comerciable < commercium < merx; commerce < commercium |
| 40 | nervoso (norm nervosus) | anorexia nervosa — An eating disorder characterized by self | OK | nervoso < nervus; anorexia nervosa cites nervosus < nervus |

**Tally: 37 correct / 1 arguable / 2 wrong — strict 37/40 = 92.5%, lenient 38/40 = 95.0%**

### The shipped payloads (real `/api/analyze` responses)

- **`conducir`** — 25 items: `conduce`, `conducive`, `conn` (direct-cognate,
  sharedRoot `conducere`/`conduco`) + the present-stem `-duc-` set via
  norm_root `ducere`/`duco` (`adduce`, `deduce`, `induce`, `produce`,
  `reduce`, `retroduce`, `seduce`, `subduce`, `subdue`, `traduce`,
  `transduce`, `transducer`, `transduction`, `adductor`, `inductor`,
  `redoubt`, `endue`, `andouille`, `nduja`, `reductive`…), each with its
  shared root and a Spanish explanation. **Notably absent by design:** the
  supine-stem words `conduct`, `product`, `duct`, `ducat`, `duchy` — they cite
  `conductus`/`productus`/`dux`, which only the rejected (c) supine bridge
  would reach. The owner's expectation of "the full -duc- set" is not met by
  option (b); the card is instead the honest, measured subset.
- **`hablar`** — `null`: the card renders the §52 Spanish empty state
  ("No se han encontrado relaciones útiles con raíces en inglés."). The
  mockup's `fable/fabulous/affable/confabulate` set remains unreachable at
  acceptable precision (see the verdict above).
