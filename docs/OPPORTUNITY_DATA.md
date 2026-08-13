# OPPORTUNITY DATA — how much of the source dictionary is sitting unused

Measured 2026-08-12 against `kaikki.org-dictionary-Spanish.jsonl` (809,603 lines, 979 MB) and
`data/morph.sqlite` (315,412,480 bytes). Read-only; nothing in the pipeline or data was changed.

## How this was measured

One streaming pass over the JSONL (`recon/measure.py`, ~19 s, ~1 GB peak memory for the
reverse-lookup term index) accumulating every counter below; `data/morph.sqlite` was opened
read-only with `sqlite3` for the frequency bands and lemma-existence checks. Raw results:
`recon/measure.json`.

Definitions:

- **lemma entry** — an entry where NOT every sense carries the `form-of`/`alt-of` tag
  (entries with no senses also count as lemmas). This is the unit a user lands on.
  Result: **117,348 lemma entries** (14.5%) and **692,255 form entries** (85.5%).
  `data/morph.sqlite` has **117,253** lemma rows — 95 fewer, because the pipeline also skips
  6 POS values (`character`, `punct`, `symbol`, `interfix`, `infix`) and all-misspelling
  entries. All percentages below are of 117,348 unless stated.
- **"all entries"** — the full 809,603-line file (form entries included), given where the
  task asked for it.

---

## 1. Usage examples

| metric | all entries | lemma entries only |
|---|---|---|
| entries with ≥1 `senses[].examples` | 15,406 (1.90%) | 14,624 (12.46%) |
| total example objects | 20,953 | 20,025 |
| examples with a `text` field | 20,664 (98.6%) | 19,752 (98.6%) |
| examples ALSO carrying an English `translation` | 9,582 (45.7%) | 9,339 (46.6%) |

- Every example carrying `translation` also carries an `english` key with the identical
  string (9,582 = 9,582) — the two are redundant; store one.
- 46.4% of text-bearing examples have a translation; the other 53.6% are Spanish-only.
- Per lemma that has any example: **median 1, mean 1.37** (max 54). Only 2,450 of the
  14,624 example-bearing lemmas (16.8%) have ≥2 examples; only 292 have ≥5.

**Sparsity flag — this is a premium, not universal, field.** 12.5% of lemmas have any
example at all, and typically just one. A "see it in a sentence" feature would be empty on
~7 of 8 lemma pages.

Five real examples, verbatim (`hacer` — 39 examples in the entry; `decir` — 15):

```json
{"text": "¿Qué haces?", "translation": "What are you doing?"}
{"text": "hacer(le) una foto a algo", "translation": "to take a picture of something"}
{"text": "hacer frío", "translation": "be cold (lit. make cold (noun))"}
{"text": "Se está haciendo tarde.", "translation": "It's getting late."}
{"text": "El cuerpo se hace a las fatigas.", "translation": "The body gets used to tiredness."}

{"text": "Es un mentiroso. Nunca dice la verdad.", "translation": "He's a liar. He never tells the truth."}
{"text": "Di que me amas.", "translation": "Say that you love me."}
{"text": "¿Cómo se dice __ en inglés?", "translation": "How do you say __ in English?"}
{"text": "Se dice que abrir un paraguas dentro de la casa da mala suerte.", "translation": "It is said that opening an umbrella inside the house gives bad luck."}
{"text": "Ya te dije que no.", "translation": "I already told you that no."}
```

**`casa` has ZERO examples** (both entries — the noun and the verb inflection). Coverage is
very uneven: `hacer` 39, `decir` 15, `casa` 0. Many high-frequency lemmas will be bare.

## 2. Pronunciation

| metric | all entries | lemma entries only |
|---|---|---|
| non-empty `sounds` array | 167,732 (20.7%) | 81,334 (69.3%) |
| ≥1 `ipa` value | 167,707 (99.98% of sound-bearing) | 81,322 (69.3% of lemmas) |
| `audio` file reference | 42 (0.005%) | **29 (0.025% of lemmas)** |
| `rhymes` | 157,739 (94.1% of sound-bearing) | 72,442 (61.7%) |
| `homophone` | 806 | 464 (0.40%) |

**Sparsity flag — audio is essentially absent from the source.** 29 lemma entries carry an
audio reference (`mp3_url`/`ogg_url`); a "hear it pronounced" button is impossible from this
data.

IPA variants per entry (lemma entries with ≥1 ipa, 81,322 total): **2 values: 61,992 (76.2%)**,
4: 14,868 (18.3%), 12: 2,197 (2.7%), 10: 1,117 (1.4%), 8: 516 (0.6%), 18: 310 (0.4%),
6: 190, 14: 11, 20: 10, 1: 7, everything else ≤ 40. The near-universal shape is
**2 values = phonemic + phonetic of one pronunciation** (`/ˈkasa/` + `[ˈka.sa]`); the
**4-value shape = both pronunciations, typically Spain + Latin America** (`/aˈθeɾ/ [aˈθeɾ]`
vs `/aˈseɾ/ [aˈseɾ]`), present on 18.3% of IPA-bearing lemmas. Entries with 10+ values are
letter names (`y`) and loans with yeísmo/regional variants (`tortilla`, `amontillado`).
`hizo`'s Spain-vs-LatAm pair from the digest is the canonical 4-value case.

`sounds` arrays, verbatim:

```json
// hacer (verb)
[{"ipa": "/aˈθeɾ/"}, {"ipa": "[aˈθeɾ]"}, {"ipa": "/aˈseɾ/"}, {"ipa": "[aˈseɾ]"}, {"rhymes": "-eɾ"}]

// hizo (verb, form entry)
[{"ipa": "/ˈiθo/"}, {"ipa": "[ˈi.θo]"}, {"ipa": "/ˈiso/"}, {"ipa": "[ˈi.so]"},
 {"rhymes": "-iθo (Equatorial Guinea, Spain)"}, {"rhymes": "-iso (Latin America, Philippines)"},
 {"homophone": "izo"}]

// casa (noun)
[{"ipa": "/ˈkasa/"}, {"ipa": "[ˈka.sa]"}, {"rhymes": "-asa"}, {"homophone": "(Latin America) caza"}]
```

## 3. Sense structure (only the FIRST gloss is stored today)

147,891 senses across 117,348 lemma entries (mean 1.26 senses/lemma).

Senses per lemma:

| senses | lemmas | % |
|---|---|---|
| 1 | 98,849 | 84.24% |
| 2 | 12,386 | 10.55% |
| 3–5 | 5,405 | 4.61% |
| 6–10 | 628 | 0.54% |
| 11+ | 80 | 0.07% |

**Keeping only the first gloss loses little for 95% of lemmas, but the 5.2% with 3+ senses
are exactly the interesting words** (common verbs/nouns); `hacer`'s 17 senses are the
pathological end, not the norm.

- 41,676 senses (28.2%) have `raw_glosses` starting with a parenthetical marker —
  `(transitive)`, `(colloquial)`, `(Mexico)` etc. 58,446 (39.5%) contain a parenthetical
  anywhere. The marker is *stripped* from the stored gloss today, so this register/domain
  info is currently thrown away.
- Senses whose `tags` indicate register (curated list: colloquial, vulgar, slang, formal,
  informal, archaic, obsolete, dated, literary, poetic, rare, uncommon, dialectal, regional,
  jocular, humorous, derogatory, offensive, euphemistic, childish, nonstandard, proscribed,
  pejorative, familiar, slur, sarcastic, ironic, endearing, neologism, jargon,
  bureaucratese, rhetoric, historical, …): **10,621 senses (7.2%)**.
- Senses whose `tags` indicate region (Mexico 2,048, Spain 1,458, El-Salvador 1,377,
  Latin-America 1,241, Chile 1,127, Honduras 925, Rioplatense 732, …): **11,054 (7.5%)**.
- Register OR region: **17,708 senses (12.0%)** — about 1 in 8 senses carries a
  register/region signal worth surfacing (a "colloquial" / "Mexico" chip).

`hacer` (verb) — all 17 senses' glosses (currently only sense 0's "to do, perform, execute,
carry out" survives into `data/morph.sqlite`):

```
[0]  to do, perform, execute, carry out
[1]  to do, perform, execute, carry out / Forms ad hoc verbs from borrowed nouns.
[2]  to make / to create, to build, to bring forth
[3]  to make / to write, to compose
[4]  to make / to prepare (food)
[5]  in various expressions about the weather          (transitive, impersonal, idiomatic)
[6]  to release, to excrete
[7]  to prep, adorn, do (a body part)
[8]  to make, to cause to be
[9]  to make, to cause to
[10] to play (a character)                             (ambitransitive, optionally with de)
[11] to become; to get                                 (reflexive, ditransitive)  ← synonyms here
[12] to become; to get / used with time                (reflexive, ditransitive)  ← synonyms here
[13] to pretend being, play                            (reflexive, ambitransitive)
[14] to move (over), scoot (over)                      (reflexive)
[15] ellipsis of hacerse el tonto                      (reflexive, Argentina)
[16] to get used to (chiefly in idioms)                (reflexive, intransitive with a)
```

## 4. Semantic relations (currently unused)

Lemma entries, top-level vs sense-level counted separately; item counts are raw items
(each item = one `{word, …}` object).

| relation | entries top-level (items) | entries sense-level (items) | distinct words | single-word | single-word existing as a lemma in morph.sqlite |
|---|---|---|---|---|---|
| `synonyms` | 104 (795) | 26,316 (54,157) | 24,250 | 19,104 | 17,070 (89.4% of single-word) |
| `antonyms` | 138 (187) | 2,024 (2,545) | 2,243 | 2,056 | 1,950 (94.8%) |
| `hypernyms` | 23 (30) | 279 (353) | 224 | 194 | 186 (95.9%) |
| `hyponyms` | 178 (1,063) | 141 (660) | 1,673 | 358 | 334 (93.3%) |
| `coordinate_terms` | 42 (138) | 404 (1,007) | 860 | 399 | 351 (88.0%) |

- **Synonyms live at sense level** (26,316 entries vs 104 top-level) and are the only
  relation with real volume. Antonyms are a distant second; hypernyms/hyponyms/
  coordinate_terms are thin (fewer than 400 single-word targets each).
- 89–96% of single-word relation targets already exist as lemmas in the DB — a
  clickable-relation feature would almost always land on a real entry.
- Note hyponyms are mostly multi-word phrases (1,315 of 1,673 distinct words, e.g. verb
  phrases) — useful as content, but not as links.

`hacer` and `casa` — verbatim synonyms/antonyms:

```json
// hacer (verb), sense 11 and sense 12 — synonyms
[{"word": "volverse"}, {"word": "convertirse en"}]
// hacer (noun), sense 0 — synonyms
[{"word": "quehacer"}, {"word": "acción"}]
// no antonyms anywhere on hacer's 2 entries

// casa — no synonyms, no antonyms on either entry
```

## 5. Reverse (English → Spanish) lookup potential

Lemma entries only, exact term matching after splitting glosses on commas/semicolons,
lowercasing and stripping (no stemming, no accent folding):

- distinct English gloss strings: **123,628** (122,506 if form-of senses are excluded)
- distinct English terms after splitting: **136,000**
- (term → lemma-entry) associations: **205,082** → **average 1.51 lemma entries per term**
  (or ~1.4 per distinct word once multi-entry lemmas like `hacer` verb+noun collapse)

Concrete queries (lemma *entries* returned; distinct words in parentheses):

| query | lemma entries | distinct words |
|---|---|---|
| `to make` | 12 | causar, confeccionar, elaborar, formular, hacer, sacar, traer, volver (8) |
| `house` | 12 | ca, casa, casalicio, casita, chante, chanti, criazón, cucurucho, domiciliar, domiciliario, hogareño, jato (12) |
| `quick` | 5 | alípede, alípedo, presto, rápido, veloz (5) |
| `to say` | 3 | decir, suponer (2) |

Verdict: viable as a **search/autocomplete accessory, not a dictionary in itself** — a term
resolves to 1–2 lemmas on average, but the hit lists mix the obvious (`casa`, `rápido`,
`decir`) with rare/regional entries (`chante`, `jato` = slang "house"; `alípede` = "swift-
footed"), so ranking by frequency (already in the DB) is essential. A plain "English word →
Spanish word" feature would return odd results without it.

## 6. Frequency banding potential (`lemma.freq`, per-million)

117,253 lemmas in `data/morph.sqlite`:

| band | lemmas | % |
|---|---|---|
| freq > 100 | 1,130 | 0.96% |
| 10 < freq ≤ 100 | 4,148 | 3.54% |
| 1 < freq ≤ 10 | 11,038 | 9.41% |
| 0.1 < freq ≤ 1 | 16,780 | 14.31% |
| 0 < freq ≤ 0.1 | 35,407 | 30.20% |
| freq = 0 | 48,750 | 41.58% |

Signal assessment: **yes, a "how common is this word" badge is worth showing.** 58.4% of
lemmas have a positive corpus frequency; the top ~14% (freq ≥ 0.1, i.e. roughly one
occurrence per 10 million words) are the everyday words, the 41.6% at exactly 0 are words
never seen in the OpenSubtitles corpus (proper names, archaic forms, coinages) — which is
itself a meaningful "not in our corpus" badge. The long tail below 0.1 is where
differentiation is noisy, but the coarse bands above have clear signal.

## 7. Size estimates (lemma entries only; added to the 315 MB `data/morph.sqlite`)

Method: the streaming pass summed `len(json.dumps(payload, ensure_ascii=False))` for each
field, lemma entries only (JSON char count ≈ UTF-8 bytes; Spanish characters are ≤2 bytes
so this undercounts by <3%). Stored estimate = payload × 1.3 (SQLite TEXT/blob + page
alignment, the same JSON-in-column style the DB already uses) + 25 B per affected row
(record overhead).

| field | payload (MB) | rows affected | stored estimate (MB) |
|---|---|---|---|
| examples (trimmed to `{text, translation}`) | 4.13 | 14,624 | ≈ 5.5–6 |
| sounds (full array) | 8.45 | 81,322 | ≈ 12–13 |
| full sense structure (`{glosses, raw_glosses, tags}` per sense) | 14.63 | 117,348 | ≈ 21–22 |
| — of which: glosses beyond the first | 0.15 | — | ≈ 0.2 (negligible) |
| semantic relations (trimmed to `{word, english, translation}`) | 3.60 | ~26,000 | ≈ 5 |
| — of which: synonyms alone | 3.21 | — | ≈ 4.5 |
| **all four combined** | **30.81** | — | **≈ 44–46 (+14–15%)** |

Notes:

- The **extra glosses** are nearly free (0.15 MB) — the bulk of the sense-structure cost is
  `raw_glosses` (which repeat the gloss plus parenthetical markers) and per-sense tags.
- Storing examples raw (with `bold_text_offsets`, `ref`, `english`) would be 7.48 MB
  payload instead of 4.13 MB.
- If relations were stored per lemma row rather than as one JSON column, add row overhead
  per (lemma, relation) pair; the payload itself is the floor either way.
- Order-of-magnitude takeaway: **nothing here is expensive.** The whole unused-value bundle
  is ~45 MB (~14% of the DB); examples, sounds, and relations together are ~25 MB. Even
  adding all of it keeps the DB under ~360 MB, and every field except full sense structure
  is a single pass-1 extraction identical in shape to what `pipeline/extract.py` already
  does.

---

## Summary of sparsity flags (things that look richer than they are)

1. **Audio: 29 lemma entries (0.025%).** A pronunciation-audio feature cannot be built from
   this source at all.
2. **Examples: 12.5% of lemmas, median 1 per lemma, and `casa` has 0.** Build the feature
   for the lemmas that have them, but expect ~7/8 lemma pages to show nothing; only 46.6%
   of the examples carry an English translation.
3. **Hypernyms/hyponyms/coordinate_terms: tiny.** 194–399 single-word targets each; only
   synonyms (19,104 single-word targets, 26,316 sense-level entries) and antonyms (2,056)
   have real volume.
4. **Senses 6+: only 0.6% of lemmas.** Multi-sense depth is concentrated in a few hundred
   common words; the first-gloss-only loss is small for the long tail.
5. **IPA is phonemic+phonetic pairs, not alternative pronunciations, for 76% of entries.**
   The Spain-vs-LatAm dual pronunciation shows up on only 18.3% of IPA-bearing lemmas.
6. **Reverse lookup works (avg 1.5 lemma entries per English term) but needs frequency
   ranking** — naive hits include slang/rare words like `chante`/`jato` for "house".

Supporting artifacts: `recon/measure.py` (the measurement pass), `recon/measure.json` (raw
counters).
