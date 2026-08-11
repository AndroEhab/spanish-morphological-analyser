# DIGEST — `kaikki.org-dictionary-Spanish.jsonl` (wiktextract / English Wiktionary, Spanish section)

Produced by `recon/extract_samples.py` (one streaming pass; 809,603 lines, 0 parse failures,
distinct words 771,237, pass runtime **12.62 s**). 46 sample entries written to
`recon/samples.jsonl`; global stats in `recon/stats.json` (contents reproduced in the final
report). All 29 requested words matched; every entry per word captured (multi-etymology /
multi-POS duplicates included).

Global key facts (from stats.json):

| metric | value |
|---|---|
| total lines | 809,603 |
| distinct `word` | 771,237 |
| entries with non-empty `forms` | 115,172 |
| entries with `etymology_text` | 66,470 |
| entries with `etymology_templates` | 62,975 |
| entries with top-level `derived` / `related` / `descendants` | 6,233 / 5,289 / 3,261 |
| entries where any sense has `form_of` or `inflection_of` | 687,217 (`inflection_of` alone: **0** — the field never appears; `form_of` is what is used) |
| of the 687,217 form-of entries: with `etymology_text` | 4,875 (1,420 of those are the boilerplate `"See the etymology of the corresponding lemma form."`) |
| entries with any sense tagged `alt-of` | 6,310 |
| distinct `pos` values | 25 |
| distinct etymology-template names | 219 |
| distinct `forms[].tags` strings | 144 |

---

## 3a. `hacer` (pos=verb) — the `forms` array

**303 form entries**, **191 distinct tag combinations**, **39 distinct tag strings**.
Form objects have exactly three keys: `"form"`, `"tags"`, `"source"` (`"source": "conjugation"`
on 296 of 303; the 7 without `source` are the head forms and alternative archaic forms):

```json
{"form": "hago",  "tags": ["first-person", "present", "singular"]}
{"form": "hice",  "tags": ["first-person", "preterite", "singular"]}
{"form": "hecho", "tags": ["participle", "past"]}
{"form": "irregular", "source": "conjugation", "tags": ["table-tags"]}
{"form": "es-conj",   "source": "conjugation", "tags": ["inflection-template"]}
{"form": "facer", "tags": ["alternative", "archaic"]}
```

7 forms without `"source"`: `hago`, `hice`, `hecho`, `facer`, `far`, `fer`, `her`.

**The full conjugation IS present** — hago, hice, hizo, haré, haga, hiciera, hiciese, hiciere,
haz, hecho, haciendo all exist as `forms[].form` values:

```json
{"form": "hago",     "tags": ["first-person", "indicative", "present", "singular"]}
{"form": "hice",     "tags": ["first-person", "indicative", "preterite", "singular"]}
{"form": "hizo",     "tags": ["indicative", "preterite", "singular", "third-person"]}
{"form": "haré",     "tags": ["first-person", "future", "indicative", "singular"]}
{"form": "haga",     "tags": ["first-person", "present", "singular", "subjunctive"], "source": "conjugation"}
{"form": "hiciera",  "tags": ["imperfect", "singular", "subjunctive", "third-person"], "source": "conjugation"}
{"form": "hiciese",  "tags": ["imperfect", "imperfect-se", "singular", "subjunctive", "third-person"], "source": "conjugation"}
{"form": "hiciere",  "tags": ["future", "singular", "subjunctive", "third-person"], "source": "conjugation"}
{"form": "haz",      "tags": ["imperative", "informal", "second-person", "singular"], "source": "conjugation"}
{"form": "hecho",    "tags": ["masculine", "participle", "past", "singular"], "source": "conjugation"}
{"form": "haciendo", "tags": ["gerund"], "source": "conjugation"}
```

**Voseo forms ARE present** (`hacés`, `hacé`):

```json
{"form": "hacés", "tags": ["indicative", "informal", "present", "second-person", "singular", "vos-form"], "source": "conjugation"}
{"form": "hacé",  "tags": ["imperative", "informal", "second-person", "singular", "vos-form"], "source": "conjugation"}
```

**Full distinct tag vocabulary for `hacer`'s 303 forms (39 tags):**

```json
["first-person","present","singular","preterite","participle","past","table-tags",
 "inflection-template","infinitive","gerund","masculine","feminine","plural","indicative",
 "informal","second-person","vos-form","third-person","imperfect","future","conditional",
 "subjunctive","imperfect-se","imperative","formal","second-person-semantically","negative",
 "combined-form","dative","object-first-person","object-singular","object-second-person",
 "object-third-person","object-plural","accusative","with-tú","with-vos","alternative","archaic"]
```

Notes:
- Redundant/homographic forms are duplicated as separate entries: `haga` appears 4×
  (pres. subj. 1sg, pres. subj. 3sg, affirmative imperative formal 3sg, negative imperative 3sg).
- `imperfect-se` marks the -se imperfect subjunctive; `vos-form` marks voseo.
- The `head_templates` of this entry: `[{"name": "es-verb", "args": {}, "expansion": "hacer (first-person singular present hago, first-person singular preterite hice, past participle hecho)"}]`
- `inflection_templates`: `[{"name": "es-conj", "args": {}}, {"name": "es-conj", "args": {"1": "hacerse"}}]`
- `hacer` also has a second, **noun** entry: `hacer m (plural haceres)` with 5 forms
  (`haceres`[plural], `facer`/`far`/`fer`/`her`[alternative, archaic]).

## 3b. `hacer` (verb) — `derived` / `related`

Top-level `derived` present: **51 entries**, each `{"word": ..., "_dis1": "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"}`,
some also carrying `"english"` + `"translation"` (Latin calques like `abolefacer`). All 51 words in full:

```
a caso hecho, a medio hacer, abolefacer, arefacer, asuefacer, benefacer, contrahacer,
deshacer, estupefacer, hace, hacer boca, hacer caca, hacer caso, hacer caso omiso,
hacer como si, hacer de cuenta, hacer el muerto, hacer gracia, hacer ilusión,
hacer la trece catorce, hacer la vertical, hacer lástima, hacer risa, hacer sitio,
hacer trampas, hacer uso de la palabra, hacer yelo, hacerlo con, hacerse a la mar,
hacerse el chancho rengo, hacerse el de las gafas, hacerse el longui, hacerse el longuis,
hacerse el que la virgen le habla, hacerse ilusiones, hacerse la de las gafas,
hacerse pasar por, hecho, madefacer, malefacer, mira lo que haces, molifacer,
no hay que hacer, patefacer, putrefacer, qué se le va a hacer, quehacer, rehacer,
rubefacer, saber hacer, satisfacer
```

No top-level `related` on the verb entry; **no sense-level `derived`/`related` either** on the
verb's 17 senses. (The **noun** `hacer` entry has sense-level `related` on its single sense:
`artefacto, estupefacto, facción, factor, factorizar, fashion, putrefacto`.)

## 3c. `hacer` (verb) — etymology, verbatim

`etymology_text`:

```json
"Etymology tree\nProto-Indo-European *dʰeh₁-\nProto-Indo-European *dʰeh₁k-\nProto-Indo-European *-yéti\nProto-Indo-European *dʰh₁kyéti\nProto-Italic *θakjō\nProto-Italic *fakjō\nLatin facere\nOld Spanish fazer\nSpanish hacer\nInherited from Old Spanish fazer, from Latin facere.\nThe first-person indicative (hago) and present subjunctive forms (haga, hagas, etc.) may have been influenced by Latin agō (compare English gesture), but more likely come from a voicing of intervocalic Latin /k/ after having dropped /i/ (e.g. Latin faciō > [ˈfa.ko] > hago)."
```

`etymology_templates` — all 13 entries, `name`+`args` verbatim; `expansion` verbatim except the
first template whose `expansion` is a 923-char HTML string with an embedded JSON blob (tree text
shown in full, HTML remainder elided at the marked cut):

```json
[
 {"name": "etymon", "args": {"1": "es", "2": ":inh", "3": "osp:fazer", "tree": "1"},
  "expansion": "Etymology tree\nProto-Indo-European *dʰeh₁-\nProto-Indo-European *dʰeh₁k-\nProto-Indo-European *-yéti\nProto-Indo-European *dʰh₁kyéti\nProto-Italic *θakjō\nProto-Italic *fakjō\nLatin facere\nOld Spanish fazer\nSpanish hacer\n[Appendix:Glossary#inherited|Inherited]] from\", \"keyword\": \"inherited\" } ], \"lang\": \"itc-pro\" }, ... [REST OF 923-CHAR HTML/JSON BLOB ELIDED]"},
 {"name": "yesno",   "args": {"1": "", "2": "i", "3": "I"}, "expansion": "I"},
 {"name": "glossary","args": {"1": "Inherited"},            "expansion": "Inherited"},
 {"name": "inh",     "args": {"1": "es", "2": "osp", "3": "fazer", "4": "", "5": "", "lit": "", "pos": "", "tr": "", "ts": "", "id": "", "sc": "", "g": "", "g2": "", "g3": "", "nocat": "", "sort": ""}, "expansion": "Old Spanish fazer"},
 {"name": "inh+",    "args": {"1": "es", "2": "osp", "3": "fazer"}, "expansion": "Inherited from Old Spanish fazer"},
 {"name": "inh",     "args": {"1": "es", "2": "la", "3": "faciō", "4": "facere"}, "expansion": "Latin facere"},
 {"name": ",",       "args": {}, "expansion": ","},
 {"name": "m+",      "args": {"1": "la", "2": "agō"}, "expansion": "Latin agō"},
 {"name": "ic",      "args": {"1": "/k/"}, "expansion": "/k/"},
 {"name": "ic",      "args": {"1": "/i/"}, "expansion": "/i/"},
 {"name": "m+",      "args": {"1": "la", "2": "", "3": "faciō"}, "expansion": "Latin faciō"},
 {"name": "ic",      "args": {"1": "[ˈfa.ko]"}, "expansion": "[ˈfa.ko]"}
]
```

## 3d. Family etymologies — `etymology_text` + `etymology_templates`

Encoding of Spanish-internal derivation vs "from Latin X" (see also 3e):

- **`af`** template (`{"name": "af", "args": {"1": "es", "2": "PREFIX", "3": "base"}}` → expansion `"PREFIX + base"`) = synchronous Spanish-internal affixation.
- **`ety` with `":af"`** in args.2 = same, inside an etymology-tree wrapper.
- **`univerbation`** = Spanish-internal univerbation.
- **`inh` / `inh+` / `ety :inh` / `etymon :inh`** = inherited (usually from Latin via Old Spanish).
- **`bor+` / `ety :bor`** = borrowed from Latin (NOT inherited).
- **`doublet`** = pairs a borrowed Latin twin with its inherited twin (factura↔hechura, factor↔hechor, facto↔hecho, faena↔hacienda).
- `cog` = cognate (other languages); `root` = PIE root node; `der` = derived-from (any language).

| word (entries) | pos | verdict | etymology_text (verbatim) | templates (name + args verbatim) |
|---|---|---|---|---|
| `deshacer` (1) | verb | **internal**: `af` des- + hacer (also inherited path via OSp/Latin) | `"Inherited from Old Spanish desfazer, from Early Medieval Latin disfacere. Synchronically des- + hacer."` | `yesno{1:"",2:"i",3:"I"}`; `glossary{1:"Inherited"}`; `inh{1:"es",2:"osp",3:"desfazer",4:"",5:"",lit:"",pos:"",tr:"",ts:"",id:"",sc:"",g:"",g2:"",g3:"",nocat:"",sort:""}` → "Old Spanish desfazer"; `inh+{1:"es",2:"osp",3:"desfazer"}`; `inh{1:"es",2:"la-eme",3:"disfacio",4:"disfacere"}` → "Early Medieval Latin disfacere"; **`af{1:"es",2:"des-",3:"hacer"}` → "des- + hacer"** |
| `rehacer` (1) | verb | **internal**: `ety :af` re- + hacer | tree: `Spanish re- / Old Spanish fazer / Spanish hacer / Spanish rehacer` + `"From re- + hacer."` | `ety{1:"es",2:":af",3:"re-",4:"hacer",text:"+",tree:"1"}` (expansion 434 chars, tree + HTML blob) |
| `satisfacer` (1) | verb | **borrowed from Latin**: `ety :bor` la:satisfaciō | tree ending `Latin satisfaciōbor. / Spanish satisfacer` + `"Borrowed from Latin satisfaciō."` | `ety{1:"es",2:":bor",3:"la:satisfaciō",text:"+",tree:"1"}` (expansion 2261 chars) |
| `hechizo` (3) | adj (etym 1), noun (etym 1), **verb (etym 2 = inflection of `hechizar`)** | adj/noun: **inherited from Latin** via OSp | `"Inherited from Old Spanish fechizo, from Latin factīcius (“artificial”, adjective), from factus (“made”) + -īcius. Compare the borrowed doublet facticio. Compare English factitious. Cognate with Portuguese feitiço."` | `etymon{1:"es",2:":inh",3:"osp:fechizo<ety:inh<la:factīcius<t:artificial><pos:adj>>>",tree:"1",text:"3"}`; `doublet{1:"es",2:"facticio",notext:"1"}`; `cog{1:"pt",2:"feitiço"}`; `root{1:"es",2:"ine-pro",3:"*dʰeh₁-"}`. Verb entry (etym 2) has **no etymology_text / no templates** — pure form-of entry. |
| `hechura` (1) | noun | **inherited from Latin** | `"Inherited from Latin factūra, from faciō + -tūra. Compare the borrowed doublet factura."` | `ety{1:"es",2:":inh",3:"la:factūra",tree:"+",text:"++"}`; `doublet{1:"es",2:"factura",notext:"1"}` |
| `hacienda` (2) | noun (etym 1), **verb (etym 2 = inflection of `hacendar`)** | noun: **inherited from Latin** via OSp | `"Inherited from Old Spanish fazienda, from Latin facienda (literally “things to be done”), from faciō (“to do”). Cognate with Portuguese fazenda. Doublet of faena."` | `yesno`; `glossary{1:"Inherited"}`; `inh{...osp:fazienda...}`; `inh+{1:"es",2:"osp",3:"fazienda"}`; `inh{1:"es",2:"la",3:"facienda",lit:"things to be done"}`; `cog{1:"pt",2:"fazenda"}`; `doublet{1:"es",2:"faena"}`. Verb entry: `ety{1:"es",nl:"1"}` → "See the etymology of the corresponding lemma form." |
| `hacedor` (1) | noun | **internal**: `ety :af` hacer + -dor | tree `Old Spanish fazer / Spanish hacer / Spanish -dor / Spanish hacedor`; text `"From hacer + -dor. Compare Portuguese fazedor, French faiseur, Italian facitore, Romanian făcător."` | `ety{1:"es",2:":af",3:"hacer",4:"-dor",text:"+",tree:"1"}`; `cog{1:"pt",2:"fazedor"}`; `cog{1:"fr",2:"faiseur"}`; `cog{1:"it",2:"facitore"}`; `cog{1:"ro",2:"făcător"}` |
| `malhechor` (1) | noun | **inherited from Latin** via OSp | `"Inherited from Old Spanish malfechor, from Late Latin malefactōrem, from Latin malefaciō. Compare Portuguese malfeitor."` | `yesno`; `glossary{1:"Inherited"}`; `inh{...osp:malfechor...}`; `inh+{1:"es",2:"osp",3:"malfechor"}`; `inh{1:"es",2:"la-lat",3:"malefactor",4:"malefactōrem"}` → "Late Latin malefactōrem"; `inh{1:"es",2:"la",3:"malefaciō"}`; `cog{1:"pt",2:"malfeitor"}` |
| `quehacer` (1) | noun | **internal**: `ety :af` que + hacer + `univerbation` | tree `Spanish que / Old Spanish fazer / Spanish hacer / Spanish quehacer`; text `"Ellipsis and univerbation of algo que hacer (“something to do”). Compare Sicilian u chi fari (“something to do”)."` | `ety{1:"es",2:":af",3:"que",4:"hacer",tree:"1"}`; `univerbation{1:"es",2:"algo que hacer",t1:"something to do",nocap:"1"}`; `cog{1:"scn",2:"u chi fari",t:"something to do"}` |
| `hechicero` (2) | noun, adj | **internal**: `ety :af` hechizo + -ero | tree ends `Spanish hechizo / Proto-Indo-European *-yósder. / Proto-Italic *-āzios / Latin -āriusnom. / Latin -ārius / Spanish -ero / Spanish hechicero`; text `"From hechizo + -ero."` | `ety{1:"es",2:":af",3:"hechizo",4:"-ero",text:"+",tree:"1"}` (expansion 5080 chars — largest in family) |
| `hacendado` (3) | adj, noun, verb | **internal**: `ety :af` hacendar + -ado (all 3 entries identical etymology) | tree `Spanish hacienda / Spanish -ar / Spanish hacendar / Spanish -ado / Spanish hacendado` + `"From hacendar + -ado."` | `ety{1:"es",2:":af",3:"hacendar",4:"-ado",text:"+",tree:"1"}` |
| `hechizar` (1) | verb | **internal**: `ety :af` hechizo + -ar | text `"From hechizo + -ar."` | `ety{1:"es",2:":af",3:"hechizo",4:"-ar",text:"+",tree:"1"}` |

Note the `hacendado` / `hechicero` / `hechizar` trees *embed* the base word's whole tree as
context: `ety :af` with `tree:"1"` renders the base's tree plus the new affix step, so the
tree itself is NOT a reliable discriminator — the args (`2:":af"`) and `etymology_text` are.

## 3e. `factura`, `factor`, `efecto` — why they are NOT the hacer family

These are **borrowed** from Latin, not inherited/derived in Spanish:

| word | pos | etymology_text (verbatim) | templates |
|---|---|---|---|
| `factura` (etym 1) | noun | `"Borrowed from Latin factūra. Compare hechura, inherited from the same source.\nIn the sense of a pastry, named by members of the Argentinian baker's union to subversively call attention to the value of their labor."` | `bor+{1:"es",2:"la",3:"factūra"}` → "Borrowed from Latin factūra"; `doublet{1:"es",2:"hechura",notext:"1"}` |
| `factura` (etym 2) | verb | `"See the etymology of the corresponding lemma form."` | `ety{1:"es",nl:"1"}` (inflection of `facturar`) |
| `factor` (etym 1) | noun | `"Borrowed from Latin factor. Compare the inherited doublet hechor (cf. malhechor)."` | `bor+{1:"es",2:"la",3:"factor"}`; `doublet{1:"es",2:"hechor",notext:"1"}`; `root{1:"es",2:"ine-pro",3:"*dʰeh₁-"}` |
| `factor` (etym 2) | noun | `"From facto (“a trufax”), from English fact, itself from Old French fact, from Latin factum. Compare with the Internet slang interjection facts used to express agreement."` | `der{1:"es",2:"en",3:"fact"}`; `der{1:"es",2:"fro",3:"fact"}`; `der{1:"es",2:"la",3:"factum"}` |
| `efecto` (1) | noun | tree ends `Latin effectusbor. / Spanish efecto` + `"Borrowed from Latin effectus."` | `ety{1:"es",2:":bor",3:"la:effectus<id:noun>",text:"+",tree:"1"}` |

**The discriminator in the data**: `bor`/`bor+`/`:bor` (borrowed) vs `inh`/`inh+`/`:inh` (inherited)
vs `af`/`:af`/`univerbation` (Spanish-internal). `doublet` pairs each borrowed word with its
inherited twin (`factura`↔`hechura`, `factor`↔`hechor`), which is the strongest "same-family"
signal *against* these being derived in Spanish. `root` (PIE `*dʰeh₁-`) is shared by both sides
and is a red herring for family grouping (it appears on `hacer`, `factor`, `hechizo`, `efecto`,
`hechura`).

## 3f. Inflected-form entries (full structure)

The link to the lemma is encoded **redundantly, 4 ways** on every inflected entry:
1. `head_templates`: `[{"name": "head", "args": {"1": "es", "2": "verb form"}, "expansion": "hizo"}]`
2. `senses[].form_of`: `[{"word": "hacer"}]`
3. `senses[].glosses`: `"third-person singular preterite indicative of hacer"` (single-string form) — or the two-string "inflection of X:" split (see `mienta`)
4. `senses[].tags`: includes `"form-of"` plus the grammatical tags
5. `senses[].links`: `[["hacer", "hacer#Spanish"]]`

These entries generally have **no `forms` array** (that's on the lemma), and often no
`etymology_text` — but *some do* (`hice` carries `"Inherited from Latin fēcī."` with an `ety`
template; others carry the boilerplate `"See the etymology of the corresponding lemma form."`).

### `hizo` (1 entry, verb) — verbatim

```json
{
 "pos": "verb",
 "head_templates": [{"name": "head", "args": {"1": "es", "2": "verb form"}, "expansion": "hizo"}],
 "word": "hizo", "lang": "Spanish", "lang_code": "es",
 "sounds": [{"ipa": "/ˈiθo/"}, {"ipa": "[ˈi.θo]"}, {"ipa": "/ˈiso/"}, {"ipa": "[ˈi.so]"},
            {"rhymes": "-iθo (Equatorial Guinea, Spain)"}, {"rhymes": "-iso (Latin America, Philippines)"},
            {"homophone": "izo"}],
 "hyphenation": ["hi‧zo"],
 "hyphenations": [{"parts": ["hi‧zo"]}],
 "senses": [
  {
   "links": [["hacer", "hacer#Spanish"]],
   "glosses": ["third-person singular preterite indicative of hacer"],
   "tags": ["form-of", "indicative", "preterite", "singular", "third-person"],
   "form_of": [{"word": "hacer"}],
   "id": "en-hizo-es-verb-SuvCt0ps",
   "categories": [{"name": "Pages with 2 entries", "kind": "other", "parents": [], "source": "w"},
                  {"name": "Pages with entries", "kind": "other", "parents": [], "source": "w"},
                  {"name": "Spanish entries with incorrect language header", "kind": "other", "parents": [], "source": "w"}]
  }
 ]
}
```

### `hice` (1 entry, verb)
Identical shape; `senses[0]` = `{"links": [["hacer","hacer#Spanish"]], "glosses": ["first-person singular preterite indicative of hacer"], "tags": ["first-person","form-of","indicative","preterite","singular"], "form_of": [{"word": "hacer"}], "id": "en-hice-es-verb-aUAzRds7", "categories": [8 category objects incl. "Pages using etymon with no ID", "Spanish entries referencing missing etymons", ...]}`. Extra vs `hizo`: it HAS `etymology_text: "Inherited from Latin fēcī."` and `etymology_templates: [{"name": "ety", "args": {"1": "es", "2": ":inh", "3": "la:fēcī", "text": "+", "tree": "1"}, "expansion": "<HTML blob>"}]`.

### `hecho` (4 entries — the multi-POS case)
| entry | etym # | pos | head_templates | senses (glosses / tags / form_of) | forms |
|---|---|---|---|---|---|
| 0 | 1 | adj | `es-adj` → "hecho (feminine hecha, masculine plural hechos, feminine plural hechas)" | ["done, completed"], ["made"] — no form_of, tags absent | `hecha`[feminine], `hechos`[masculine,plural], `hechas`[feminine,plural] |
| 1 | 1 | verb | `es-past participle` → same expansion | ["past participle of hacer"], tags `["form-of","participle","past"]`, `form_of: [{"word":"hacer"}]` | same 3 |
| 2 | 2 | noun | `es-noun {1:m}` → "hecho m (plural hechos)" | ["fact"] tag `["archaic","masculine"]`; ["act, deed"]; ["act of hatching a plan or an idea"] | `hechos`[plural], `fecho`[alternative], `facto`[alternative] |
| 3 | 3 | verb | `head {1:"es",2:"misspelling"}` → "hecho" | ["misspelling of echo"], tags `["alt-of","misspelling"]`, **no form_of** — link is `links: [["echo","echo#Spanish"]]` | none |

Etymologies: entry 0/1: `"Inherited from Latin factus. Doublet of facto."` (+`etymon` tree,
`doublet{1:"es",2:"facto"}`); entry 2: `"From Latin factum n."`; entry 3: `"See the etymology of the corresponding lemma form."`

### `canté` (1 entry, verb)
Same shape as `hizo`: head `verb form`; `senses[0] = {"links":[["cantar","cantar#Spanish"]], "glosses":["first-person singular preterite indicative of cantar"], "tags":["first-person","form-of","indicative","preterite","singular"], "form_of":[{"word":"cantar"}], "id":"en-canté-es-verb-vm9qQaSE", "categories":[...3...]}`.

### `mienta` — THE AMBIGUITY TEST CASE (1 entry, 4 senses, TWO lemmas)

There is exactly **one** entry with `word == "mienta"`, pos=verb, no sounds/hyphenation/forms.
Its 4 senses point to **two different lemmas** (`mentar` ×2 and `mentir` ×2), disambiguated only
by per-sense tags. The gloss is the two-string `["inflection of X:", "description"]` split —
a distinct pattern from `hizo`'s single-string gloss. Verbatim:

```json
{
 "pos": "verb",
 "head_templates": [{"name": "head", "args": {"1": "es", "2": "verb form"}, "expansion": "mienta"}],
 "word": "mienta", "lang": "Spanish", "lang_code": "es",
 "senses": [
  {
   "links": [["mentar", "mentar#Spanish"]],
   "form_of": [{"word": "mentar"}],
   "glosses": ["inflection of mentar:", "third-person singular present indicative"],
   "tags": ["form-of", "indicative", "present", "singular", "third-person"],
   "id": "en-mienta-es-verb-pLd6yeHF",
   "categories": [{"name": "Pages with 1 entry", "kind": "other", "parents": [], "source": "w+disamb", "_dis": "51 4 42 4"}, ...]
  },
  {
   "links": [["mentar", "mentar#Spanish"]],
   "form_of": [{"word": "mentar"}],
   "glosses": ["inflection of mentar:", "second-person singular imperative"],
   "tags": ["form-of", "imperative", "second-person", "singular"],
   "id": "en-mienta-es-verb-HezMWP3e"
  },
  {
   "links": [["mentir", "mentir#Spanish"]],
   "form_of": [{"word": "mentir"}],
   "glosses": ["inflection of mentir:", "first/third-person singular present subjunctive"],
   "tags": ["first-person", "form-of", "present", "singular", "subjunctive", "third-person"],
   "id": "en-mienta-es-verb-D97w6W-M",
   "categories": [{"name": "Pages with 1 entry", "kind": "other", "parents": [], "source": "w+disamb", "_dis": "51 4 42 4"}, ...]
  },
  {
   "links": [["mentir", "mentir#Spanish"]],
   "form_of": [{"word": "mentir"}],
   "glosses": ["inflection of mentir:", "third-person singular imperative"],
   "tags": ["form-of", "imperative", "singular", "third-person"],
   "id": "en-mienta-es-verb-U-26v9Bx"
  }
 ]
}
```

Per-sense table: | sense | lemma (`form_of[0].word`) | tags | glosses |
|---|---|---|---|
| 0 | mentar | form-of, indicative, present, singular, third-person | "inflection of mentar:", "third-person singular present indicative" |
| 1 | mentar | form-of, imperative, second-person, singular | "inflection of mentar:", "second-person singular imperative" |
| 2 | mentir | first-person, form-of, present, singular, subjunctive, third-person | "inflection of mentir:", "first/third-person singular present subjunctive" |
| 3 | mentir | form-of, imperative, singular, third-person | "inflection of mentir:", "third-person singular imperative" |

(For reference: lemma `mentar` = `es-verb {1:"<ie>"}` → "mentar (first-person singular present
miento, first-person singular preterite menté, past participle mentado)"; lemma `mentir` =
`es-verb {1:"<ie-i>"}` → "mentir (first-person singular present miento, first-person singular
preterite mentí, past participle mentido)".)

## 3g. Do standalone entries exist for inflected forms? — YES, all 12 checked

`word_exists_check` from the single streaming pass (exact `word` equality, any pos):

| word | standalone entry exists |
|---|---|
| hago | true |
| haces | true |
| hice | true |
| hizo | true |
| hacíais | true |
| haríais | true |
| hagáis | true |
| hiciera | true |
| hicieseis | true |
| hiciere | true |
| hiciéremos | true |
| haré | true |

So every inflected form is BOTH a row in the lemma's `forms` array AND (in these cases) a
standalone entry with `senses[].form_of` → lemma.

## 3h. `pos` values (exact strings, all 25) + noun gender/number forms

```json
["verb","noun","adj","name","adv","suffix","phrase","intj","prefix","pron","prep","num",
 "proverb","conj","det","character","prep_phrase","contraction","symbol","article","particle",
 "punct","interfix","infix","adv_phrase"]
```

Counts: verb 585,527 | noun 129,731 | adj 75,946 | name 8,715 | adv 5,130 | suffix 1,087 |
phrase 814 | intj 727 | prefix 330 | pron 292 | prep 257 | num 250 | proverb 234 | conj 168 |
det 146 | character 76 | prep_phrase 68 | contraction 50 | symbol 20 | article 16 | particle 10 |
punct 6 | interfix 1 | infix 1 | adv_phrase 1. (No "(none)": every entry has `pos`.)

Noun/adj gender-number forms are plain `forms[].tags` with `feminine`/`masculine`/`plural`,
plus the inflection spelled out in `head_templates.expansion`:

```json
// hacedor (noun, es-noun {1:"m", f:"+"} → "hacedor m (plural hacedores, feminine hacedora, feminine plural hacedoras)")
{"form": "hacedores", "tags": ["plural"]}
{"form": "hacedora",  "tags": ["feminine"]}
{"form": "hacedoras", "tags": ["feminine", "plural"]}

// hecho (adj, es-adj → "hecho (feminine hecha, masculine plural hechos, feminine plural hechas)")
{"form": "hecha",  "tags": ["feminine"]}
{"form": "hechos", "tags": ["masculine", "plural"]}
{"form": "hechas", "tags": ["feminine", "plural"]}

// casa (noun)
{"form": "casas", "tags": ["plural"]}

// hacer (noun) — also carries alternative forms
{"form": "haceres", "tags": ["plural"]}
{"form": "facer", "tags": ["alternative", "archaic"]}
```

## 3i. Language coverage — MONOLINGUAL

All 809,603 entries: `"lang": "Spanish"`, `"lang_code": "es"`. No other languages in the file
(the file is the Spanish section of English Wiktionary; cross-language info appears only inside
`etymology_templates` args and `cog`/`der` templates).

## 3j. `links` / `raw_glosses` / `redirect` + other grouping aids

- `senses[].links` — present on most senses: `[["do","do"],["perform","perform"],["execute","execute"],["carry out","carry out"]]` (each item is `[display, target]`, target often `"word#Spanish"`).
- `senses[].raw_glosses` — present alongside `glosses` on lemma senses: `["(transitive) to do, perform, execute, carry out"]` (glosses drop the parenthetical).
- `redirect` — **never appears** (0 entries; not in the top-level key histogram).
- `inflection_of` — never appears (0 entries); `form_of` is the field that exists.
- Other grouping-useful keys present:
  - `etymology_number` — 10,121 entries; values `"1"`..`"6"` ("1": 5,036, "2": 4,619, "3": 396, "4": 59, "5": 9, "6": 2). Multiple etymologies = multiple entries sharing `word`.
  - `head_templates` — 809,287 entries (name = `es-verb`/`es-noun`/`es-adj`/`head`/`es-past participle`/...); the `head` + args.2 `"verb form"` pattern marks inflections.
  - `inflection_templates` — 8,865 entries (e.g. `es-conj`), on lemmas with full conjugation tables.
  - `wikipedia` — 413; `categories` top-level — 1,821.
  - sense-level `derived` (9,201 entries) / `related` (12,795) / `descendants` (0) — note `related`/`derived` can live at top level OR inside senses (hacer-noun's `related` is sense-level).
  - sense `id` strings: `"en-<word>-<pos>-<random>"` (unique per sense).
  - category objects from `w+disamb` carry `_dis` disambiguation weight strings (e.g. `"51 4 42 4"`) — potentially usable as a heuristic weight per sense.
  - `senses[].synonyms` / `antonyms` (top-level too), `examples` with `bold_text_offsets`/`translation`.

## Sample multiplicity

`sample_word_counts` (all entries captured per word): cantar 2, canté 1, casa 2, casita 1,
comer 2, correr 2, deshacer 1, efecto 1, factor 2, factura 2, hacedor 1, hacendado 3, hacer 2,
hacienda 2, hechicero 2, hechizar 1, hechizo 3, hecho 4, hechura 1, hice 1, hizo 1,
malhechor 1, mentar 1, mentir 1, mienta 1, quehacer 1, rehacer 1, satisfacer 1, vivir 2.
