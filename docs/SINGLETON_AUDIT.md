# Singleton audit — why 66.2% of lemmas sit in a family of one

Read-only diagnostic study. Data: `kaikki.org-dictionary-Spanish.jsonl` (809,603 lines, streamed once) and
`data/morph.sqlite` (117,253 lemmas, 88,137 families, built 2026-08-13). No pipeline code was changed;
nothing was committed. Companion artifacts (all under `recon/`): `singleton_audit.py` (the streaming pass),
`singleton_audit_targets.json` (the 607 audited lemmas with prefix mates),
`singleton_audit_evidence.json` (per-lemma etymology/derived/related/synonym evidence),
`singleton_audit_classification.json` (final A/B/C/D classification with reasons).

## Method

- **Unit of analysis** — a DB lemma row `(word, pos, etym_no)`. A *singleton* is a lemma whose family has
  size 1 (77,612 of 117,253 = **66.19%**).
- **Task 1** — the complete population of 367 singletons with `freq >= 100` per million, exhaustively
  classified (no sampling).
- **Task 2** — 60 singletons sampled from each of four bands (seeded `random.Random(42)` over the sorted
  singleton pool of each band): `10 <= freq < 100`, `1 <= freq < 10`, `0 < freq < 1`, `freq == 0`.
- For every entry I extracted from the JSONL: `etymology_text` presence, `etymology_templates` (names),
  top- + sense-level `derived`/`related` items (single-word, with "exists as a DB lemma" flags), and
  `synonyms`. Affix-template bases were parsed with the pipeline's own `pipeline.etymology.parse_templates`,
  and gate blocking was verified against the pipeline's actual E1/E4/E4b/E5 code and the intermediate
  `data/lemmas.jsonl` (forms, stored templates).
- **Prefix mates** — other DB lemmas sharing a ≥5-character accent-folded prefix, sorted by frequency,
  shown up to 5 (`~` = same word, different POS entry).

### Classification rules (applied conservatively)

- **A — genuinely atomic.** Proper nouns (`pos=name`), function words (`prep, conj, pron, det, article,
  particle, num, intj`), bound morphemes (`suffix, prefix`), multi-word expressions, loanwords with no
  Spanish derivatives, and basic roots with no derivatives *anywhere in the DB*. Correct outcome; nothing
  to fix.
- **B — Wiktionary has no etymology at all** for the entry (no etymology text, no templates, no
  derived/related lists) *and* no plausible relative exists in our DB.
- **C — Wiktionary has usable evidence we are not extracting or are extracting wrongly.** An affix-style
  template, a `derived`/`related` list, or an etymology naming a Spanish parent, where the named word
  **exists as a lemma in our DB** and the relation is linguistically real. Each C is itemised with the
  specific evidence and the mechanism that drops it.
- **D — a plausible relative exists as a lemma in our DB but no dictionary evidence connects them.**
  Recoverable only by inference, which this project deliberately refuses. Strict on false friends
  (`casa`/`casino`, `soportal`/`soportar`, `colina`/`colín` are rejected).
- Conservative policy: a closed-class/name entry carrying derivational evidence stays **A** — its being
  family-less is expected and the evidence is recorded as a boundary case (§9), not as C.

## 0. Frequency-weighted context (reproduced)

| band | lemmas | singletons | singleton rate |
|---|---|---|---|
| all | 117,253 | 77,612 | **66.19%** |
| freq > 0 | 68,503 | 36,340 | **53.05%** |
| freq >= 1 | 16,316 | 6,195 | **37.97%** |
| freq >= 10 | 5,278 | 1,609 | **30.49%** |
| freq >= 100 | 1,130 | 367 | **32.48%** |

These reproduce the stated 66.2 / 53.0 / 38.0 / 30.5 / 32.5 figures exactly.

## 1. The 367 high-frequency singletons (freq >= 100), exhaustive

Columns: **etym** = has etymology text or templates; **tpl** = etymology template names;
**der/rel** = derived/related items as `single-word/items-existing-as-lemmas` (`+nw` = multi-word items);
**syn** = synonym items; **mates** = ≤5 DB lemmas sharing a ≥5-char prefix
(`word(pos,freq,famsize)`, `~` = same word); **cls** = class, with the one-line reason.

| # | word | pos | gloss | freq | etym | tpl | der | rel | syn | mates (≤5) | cls | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | de | noun | The name of the Latin script letter D/d. | 34160 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 2 | de | prep | of; 's; used after the thing owned and before th… | 34160 | Y | cog,etymon | 40/29+1w | 3/3 | 4 | — | **A** | function word (prep) — family-less expected |
| 3 | que | conj | that | 34069 | Y | cog,ety,glossary,inh,inh+,m+,yesno | — | — | 0 | — | **A** | function word (conj) — family-less expected |
| 4 | que | pron | who; that | 34069 | Y | cog,ety,glossary,inh,inh+,m+,yesno | 3/3+12w | 1/1 | 0 | — | **A** | function word (pron) — family-less expected |
| 5 | no | adv | not | 29246 | Y | cog,glossary,inh,inh+,yesno | 0/0+12w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 6 | no | intj | no | 29246 | Y | cog,glossary,inh,inh+,yesno | 1/1 | — | 0 | — | **A** | function word (intj) — family-less expected |
| 7 | no | noun | no | 29246 | Y | cog,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 8 | -(a) | suffix | Added to the end of a masculine word for gender-… | 22560 | Y | — | — | — | 0 | — | **A** | bound morpheme — not a family member |
| 9 | A | noun | bishop | 22560 | Y | abbrev | — | — | 0 | — | **C** | abbrev template 'Abbreviation of alfil' names alfil (lemma ✓); abbrev template type is not parsed |
| 10 | a | prep | to | 22560 | Y | ety | 0/0+7w | — | 0 | — | **A** | function word (prep) — family-less expected |
| 11 | a | intj | Used to express indiference or sarcasm. | 22560 | N | — | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 12 | ah | intj | ah (expression of relief, realization, awe) | 22560 | Y | cog,onomatopoeic | — | 6/6 | 0 | — | **A** | function word (intj) — family-less expected |
| 13 | el | article | masculine singular definite article; the | 21558 | Y | cog,false cognate,glossary,inh | 0/0+2w | 3/3 | 0 | — | **A** | function word (article) — family-less expected |
| 14 | la | article | feminine singular definite article; the | 21558 | Y | etymon,inh | — | — | 0 | — | **A** | function word (article) — family-less expected |
| 15 | la | pron | impersonal neuter pronoun (accusative) in certai… | 21558 | Y | etymon,inh | 5/2+2w | 33/27+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 16 | la | noun | la (sixth note of the scale) | 21558 | Y | etymon | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 17 | el | article | feminine singular definite article used before n… | 17792 | Y | der,inh | — | — | 0 | — | **A** | function word (article) — family-less expected |
| 18 | e | conj | and | 16841 | Y | ety | — | 1/1 | 0 | — | **A** | function word (conj) — family-less expected |
| 19 | y | conj | and | 16841 | Y | ety,glossary,inh,inh+,yesno | 0/0+8w | — | 0 | — | **A** | function word (conj) — family-less expected |
| 20 | e | noun | The name of the Latin script letter E/e. | 16522 | Y | — | 0/0+1w | — | 0 | — | **B** | letter-name entry; only a 'See Translingual section' pointer — no etymology at all |
| 21 | en | prep | in, at, on | 16106 | Y | inh | 0/0+13w | — | 0 | — | **A** | function word (prep) — family-less expected |
| 22 | lo | article | neuter definite article used only before nominal… | 14273 | Y | cog,glossary,inh,inh+,yesno | 0/0+2w | — | 0 | — | **A** | function word (article) — family-less expected |
| 23 | un | article | an; a | 13243 | Y | glossary,inh,inh+,yesno | 0/0+8w | — | 0 | — | **A** | function word (article) — family-less expected |
| 24 | por | prep | by | 10524 | Y | doublet,ety,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (prep) — family-less expected |
| 25 | por | intj | why? | 10524 | Y | doublet,ety,glossary,inh,inh+,yesno | 1/1+233w | 1/1 | 0 | — | **A** | function word (intj) — family-less expected |
| 26 | qué | det | what; which | 9844 | Y | ety | — | — | 1 | — | **A** | function word (det) — family-less expected |
| 27 | qué | adv | how | 9844 | Y | ety | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 28 | qué | pron | what | 9844 | Y | ety | — | — | 0 | — | **A** | function word (pron) — family-less expected |
| 29 | qué | intj | what (expresses surprise or confusion) | 9844 | Y | ety | 1/1+12w | 2/2 | 1 | — | **A** | function word (intj) — family-less expected |
| 30 | una | pron | one (an indefinite plural pronoun using a singul… | 9087 | Y | der,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (pron) — family-less expected |
| 31 | uno | num | one | 9087 | Y | cog,doublet,ety,glossary,inh,inh+,yesno | 0/0+8w | — | 0 | — | **A** | function word (num) — family-less expected |
| 32 | uno | det | one | 9087 | Y | cog,doublet,ety,glossary,inh,inh+,yesno | — | 4/4 | 0 | — | **A** | function word (det) — family-less expected |
| 33 | uno | pron | one | 9087 | Y | cog,doublet,ety,glossary,inh,inh+,yesno | 0/0+1w | — | 0 | — | **A** | function word (pron) — family-less expected |
| 34 | unx | article | a/an | 9087 | N | — | — | — | 0 | — | **A** | function word (article) — family-less expected |
| 35 | los | pron | plural masculine or neuter pronoun | 7251 | Y | glossary,inh,inh+,yesno | — | 32/26+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 36 | se | pron | A reflexive or reciprocal pronoun: oneself, hims… | 7225 | Y | ety | — | — | 0 | — | **A** | function word (pron) — family-less expected |
| 37 | se | pron | used instead of indirect object pronouns le and … | 7225 | Y | cog,inh | — | — | 0 | — | **A** | function word (pron) — family-less expected |
| 38 | sé | intj | yes | 7225 | Y | — | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 39 | te | noun | The name of the Latin script letter T/t. | 7169 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 40 | te | pron | yourself | 7169 | Y | inh | — | 32/26+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 41 | tú | pron | you (second-person singular pronoun) | 7169 | Y | cog,glossary,inh,inh+,yesno | 2/2+3w | 32/26+10w | 4 | — | **A** | function word (pron) — family-less expected |
| 42 | vos | pron | you, familiar form of the second-person singular… | 7169 | Y | glossary,inh,inh+,yesno | 3/3+1w | 32/26+10w | 1 | — | **A** | function word (pron) — family-less expected |
| 43 | con | prep | with | 7154 | Y | cog,glossary,inh,inh+,yesno | 1/1+7w | 5/5 | 0 | — | **A** | function word (prep) — family-less expected |
| 44 | para | prep | for, to (expressing a recipient) | 6691 | Y | ety,inh | 0/0+23w | 1/1 | 2 | — | **A** | function word (prep) — family-less expected |
| 45 | para | noun | paramilitary | 6691 | Y | etymon | — | — | 1 | — | **C** | prose 'Clipping of paramilitar' (lemma ✓); clipping not parsed |
| 46 | mi | noun | mu; the Greek letter Μ, μ | 5677 | N | — | — | — | 1 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 47 | mi | noun | mi | 5677 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 48 | perar | verb | apheretic form of esperar (“to wait”) | 5598 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 49 | sí | particle | yes, yeah, (used to respond affirmatively to a q… | 5553 | Y | glossary,inh,inh+,yesno | 0/0+4w | — | 2 | — | **A** | function word (particle) — family-less expected |
| 50 | sí | intj | hello? (used when answering a phone call) | 5553 | Y | glossary,inh,inh+,yesno | — | — | 6 | — | **A** | function word (intj) — family-less expected |
| 51 | sí | noun | yes; aye, ay; approbation, acceptance | 5553 | Y | glossary,inh,inh+,yesno | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 52 | sí | pron | prepositional form of se | 5553 | Y | cog,glossary,inh,inh+,yesno | 0/0+7w | 33/27+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 53 | si | conj | if, whether | 5549 | Y | ety | 0/0+19w | 1/1 | 0 | — | **A** | function word (conj) — family-less expected |
| 54 | ése | pron | that one | 4795 | Y | defdate,glossary,inh,inh+,yesno | — | 4/4 | 0 | — | **A** | function word (pron) — family-less expected |
| 55 | Su | name | a diminutive of the female given name Susana | 4738 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 56 | su | det | apocopic form of suyo | 4738 | Y | glossary,inh,inh+,yesno | 0/0+1w | 25/12 | 0 | — | **A** | function word (det) — family-less expected |
| 57 | las | article | feminine plural definite article; the | 4728 | Y | glossary,inh,inh+,yesno | — | 3/3 | 0 | — | **A** | function word (article) — family-less expected |
| 58 | las | pron | feminine plural pronoun | 4728 | N | — | — | — | 0 | — | **A** | function word (pron) — family-less expected |
| 59 | del | contraction | of the, from the (+ a masculine noun in singular… | 3893 | Y | cog | — | 1/1 | 0 | — | **A** | function word (contraction) — family-less expected |
| 60 | Como | name | Como (a city and comune, the capital of the prov… | 3852 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 61 | como | adv | as (to such an extent or degree) | 3852 | Y | cog,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 62 | como | conj | as (introducing a basis of comparison or equalit… | 3852 | Y | cog,glossary,inh,inh+,yesno | — | — | 2 | — | **A** | function word (conj) — family-less expected |
| 63 | como | prep | as (in the manner or role specified) | 3852 | Y | cog,glossary,inh,inh+,yesno | 1/1+13w | — | 2 | — | **A** | function word (prep) — family-less expected |
| 64 | al | contraction | upon | 3661 | N | — | — | 1/1 | 0 | — | **A** | function word (contraction) — family-less expected |
| 65 | más | adv | more; -er (used to make comparisons) | 3552 | Y | cog,glossary,inh,inh+,yesno | 0/0+38w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 66 | más | det | more, any more | 3552 | Y | cog,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (det) — family-less expected |
| 67 | más | conj | plus | 3552 | Y | cog,glossary,inh,inh+,yesno | 1/1+13w | — | 0 | — | **A** | function word (conj) — family-less expected |
| 68 | elle | pron | they, them (singular); a gender-neutral singular… | 3383 | N | — | — | 33/27+11w | 0 | — | **A** | function word (pron) — family-less expected |
| 69 | le | pron | to him, for him; dative of él | 3383 | Y | der | — | 32/26 | 5 | — | **A** | function word (pron) — family-less expected |
| 70 | le | pron | to them, for them (singular); dative of elle | 3383 | Y | der | — | 32/26 | 5 | — | **A** | function word (pron) — family-less expected |
| 71 | esto | pron | substitutes a noun one can't remember or can't r… | 3066 | Y | inh | — | 33/27+10w | 2 | — | **A** | function word (pron) — family-less expected |
| 72 | éste | pron | this one | 3066 | Y | ety | — | 4/4 | 1 | — | **A** | function word (pron) — family-less expected |
| 73 | todo | det | all; every | 3064 | Y | cog,glossary,inh,inh+,yesno | — | — | 1 | — | **A** | function word (det) — family-less expected |
| 74 | todo | pron | everything | 3064 | Y | cog,glossary,inh,inh+,yesno | 2/2+59w | — | 0 | — | **A** | function word (pron) — family-less expected |
| 75 | ya | adv | now, right now, (in the negative) anymore, no lo… | 2635 | Y | ,,cog,glossary,inh,inh+,yesno | 1/0+20w | — | 3 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 76 | ya | conj | first (something) then (something else); first (… | 2635 | Y | ,,cog,glossary,inh,inh+,yesno | — | — | 1 | — | **A** | function word (conj) — family-less expected |
| 77 | ya | intj | come on!, let's go! | 2635 | Y | ,,cog,glossary,inh,inh+,yesno | 0/0+1w | — | 9 | — | **A** | function word (intj) — family-less expected |
| 78 | este | det | this | 2485 | Y | ety | — | — | 0 | — | **A** | function word (det) — family-less expected |
| 79 | así | adv | like this; like that; as such; thus; so; thereby… | 2481 | Y | cog,glossary,inh,inh+,yesno | 2/2+20w | 0/0+2w | 1 | — | **C** | derived asá/asimismo ✓; source adv has no forms |
| 80 | ir | verb | to go (away from speaker and listener) | 2479 | Y | dercat,glossary,ic,inh,inh+,lg,yesno | 0/0+65w | 4/4 | 3 | — | **A** | suppletive verb; related list names only synonyms (andar, caminar, ser, marchar) |
| 81 | vamos | intj | let's go! | 2479 | Y | der | — | — | 3 | vamos a ver(phrase,0,1), vamos al caso(phrase,0,1), vamos hablando(phrase,0,1) | **A** | function word (intj) — family-less expected |
| 82 | algo | pron | something, anything | 2455 | Y | glossary,inh,inh+,yesno | 0/0+6w | 2/2 | 1 | — | **A** | function word (pron) — family-less expected |
| 83 | algo | adv | rather, somewhat, kind of | 2455 | Y | glossary,inh,inh+,yesno | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 84 | Bueno | name | a surname | 2392 | N | — | — | — | 0 | ~bueno(adj,2392,15), ~bueno(intj,2392,15), buenorro(adj,1,15), buenota(noun,0,16), buenón(adj,0,15) | **A** | proper noun — family-less expected |
| 85 | ella | pron | she, her (used subjectively and after prepositio… | 2201 | Y | glossary,inh,inh+,yesno | — | 32/26+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 86 | él | pron | he, him, masculine personal third person subject… | 2201 | Y | ety | — | 33/27+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 87 | tú | intj | , Spain) expletive | 2140 | Y | cog,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 88 | nos | pron | first person (except in vocative, and in the obl… | 2048 | Y | glossary,inh,inh+,yesno | 1/1+2w | — | 0 | — | **A** | function word (pron) — family-less expected |
| 89 | de nada | intj | it's nothing, think nothing of it, you're welcom… | 2041 | N | — | — | — | 2 | ~de nada(adj,2041,1), de natura(adv,0,1), de narices(adj,0,1), de nacimiento(adj,0,1) | **A** | multi-word expression — family-less expected |
| 90 | de nada | adj | insignificant, of little importance | 2041 | N | — | — | — | 0 | ~de nada(intj,2041,1), de natura(adv,0,1), de narices(adj,0,1), de nacimiento(adj,0,1) | **A** | multi-word set phrase; no derivational relatives |
| 91 | nada | pron | nothing, zero, zilch, not...anything | 2041 | Y | ety,glossary,inh,inh+,ncog,yesno | 3/0+33w | 2/2 | 1 | — | **A** | function word (pron) — family-less expected |
| 92 | nada | noun | nothingness, nothing | 2041 | Y | ety,glossary,inh,inh+,ncog,yesno | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 93 | nada | adv | not at all | 2041 | Y | ety,glossary,inh,inh+,ncog,yesno | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 94 | este | intj | uh, well (space filler in a conversation) | 2029 | Y | ety | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 95 | este | noun | east | 2029 | Y | bor+,cog,der,wp | — | 1/1 | 2 | — | **A** | borrowed from French est; related oriental has a different Latin root — semantic, not derivational |
| 96 | o | conj | or | 1994 | Y | ety,glossary,inh,inh+,yesno | 0/0+1w | — | 0 | — | **A** | function word (conj) — family-less expected |
| 97 | o | conj | either … or | 1994 | Y | ety,glossary,inh,inh+,yesno | 0/0+1w | — | 0 | — | **A** | function word (conj) — family-less expected |
| 98 | o | adv | where | 1994 | Y | ety,glossary,inh,inh+,yesno | 2/1+1w | — | 1 | — | **A** | from Latin ubi; the derived 'do' target in DB is the musical note (homonym coincidence) |
| 99 | Gracias | name | a colonial town in the Lempira department of Hon… | 1842 | N | — | — | — | 0 | gracia(noun,1842,9), ~gracias(intj,1842,1), ~gracias(noun,1842,1), gracioso(adj,93,4), gracioso(noun,93,4) | **A** | proper noun — family-less expected |
| 100 | gracias | intj | thank you, thanks | 1842 | Y | der | — | — | 0 | gracia(noun,1842,9), ~Gracias(name,1842,1), ~gracias(noun,1842,1), gracioso(adj,93,4), gracioso(noun,93,4) | **A** | function word (intj) — family-less expected |
| 101 | gracias | noun | thanks | 1842 | Y | der | 0/0+11w | 2/2 | 0 | gracia(noun,1842,9), ~Gracias(name,1842,1), ~gracias(intj,1842,1), gracioso(adj,93,4), gracioso(noun,93,4) | **C** | related gracia ✓ ('gracias' contains 'gracia', substring passes) + agradecer ✓; source ineligible: gracias noun has NO form records |
| 102 | era | noun | era, age | 1809 | Y | ety | 0/0+4w | — | 0 | — | **A** | borrowed from Late Latin aera; homograph era 'threshing floor' has a distinct etymon (ārea) and is correctly split |
| 103 | era | noun | threshing floor | 1809 | Y | doublet,glossary,inh,inh+,yesno | — | — | 0 | — | **C** | doublet template names área (lemma ✓) — doublet edges parsed in build.py but never loaded into FamilyBuilder |
| 104 | porque | conj | because | 1618 | Y | ety | 0/0+2w | 1/1+1w | 2 | ~porqué(noun,79,1), porquería(noun,17,4), porquero(noun,0,1), porqueriza(noun,0,1), porquerizo(noun,0,1) | **A** | function word (conj) — family-less expected |
| 105 | sabes | intj | you know? (rhetorical question) | 1504 | N | — | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 106 | puede | intj | it's possible; could be | 1491 | N | — | — | — | 0 | puede que(adv,0,1), puede ayudarme(phrase,0,1), puedes ayudarme(phrase,0,1) | **A** | function word (intj) — family-less expected |
| 107 | ere | noun | The name of the Latin script letter R/r. | 1488 | N | — | 0/0+1w | — | 1 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 108 | usted | pron | second person formal; you (singular) | 1462 | Y | abbr,bor,cog | 1/1 | 32/26+10w | 8 | ustedes(pron,1462,1), ustedear(verb,0,1), ustedeo(noun,0,1) | **A** | function word (pron) — family-less expected |
| 109 | ustedes | pron | you (plural), you guys, y'all, yous, yinz, ye | 1462 | Y | — | — | 32/26+10w | 1 | usted(pron,1462,1), ustedear(verb,0,1), ustedeo(noun,0,1) | **A** | function word (pron) — family-less expected |
| 110 | entonces | adv | then, next, thereupon, at that time, at that poi… | 1441 | Y | cog,glossary,inh,inh+,yesno | 0/0+9w | 1/1 | 0 | entonar(verb,1,10), entonación(noun,0,10), entonador(noun,0,1), entontecer(verb,0,14) | **A** | from Latin in+tunce; related pues is not a derivation |
| 111 | hola | intj | hello, hi, hey | 1421 | Y | cog,der,ncog | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 112 | tan | adv | so, as | 1356 | Y | glossary,inh,inh+,yesno | — | — | 1 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 113 | tan | det | such, such a | 1356 | Y | glossary,inh,inh+,yesno | 0/0+2w | — | 0 | — | **A** | function word (det) — family-less expected |
| 114 | quién | pron | who?, whom?; (with “de”) whose? | 1338 | Y | ety | 0/0+3w | — | 0 | ~quien(pron,442,1), quiénes(pron,54,1), quienquiera(pron,10,17), quién va(phrase,0,1), quienquita(intj,0,1) | **A** | function word (pron) — family-less expected |
| 115 | sus | det | your (with plural possessee) | 1328 | Y | inh | — | 25/12 | 0 | — | **A** | function word (det) — family-less expected |
| 116 | sus | intj | c'mon; attaboy | 1328 | N | — | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 117 | sus | adj | sus | 1328 | Y | bor+ | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 118 | do | noun | do (musical note) | 1315 | Y | bor | — | 6/6 | 0 | — | **A** | borrowed from Italian (solmization); related list is the solfège scale, not relatives |
| 119 | nunca | adv | never | 1299 | Y | glossary,inh,inh+,yesno | 0/0+13w | — | 2 | nunca más(adv,0,1), nuncamente(adv,0,1), nunca jamás(adv,0,1), nunca se sabe(phrase,0,1), nunca digas nunca(proverb,0,1) | **A** | from Latin numquam; no derivatives in the dictionary |
| 120 | dónde | adv | where?; in what place? | 1275 | Y | — | 1/0+5w | 2/2 | 1 | ~dónde(noun,1275,2), ~donde(adv,656,1), ~donde(conj,656,1), ~donde(prep,656,1), ~donde(pron,656,1) | **C** | related adónde/donde ✓; substring gate is RAW-case ('dónde' ⊅ 'donde'); source adv has no forms |
| 121 | va | intj | okay | 1265 | Y | — | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 122 | oh | intj | oh (expression of awe, surprise, pain or realiza… | 1259 | N | — | — | 2/2 | 0 | — | **A** | function word (intj) — family-less expected |
| 123 | mí | pron | me; (declined form of yo used as the object of a… | 1218 | Y | glossary,inh,inh+,yesno | 0/0+2w | 32/26+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 124 | Señor | name | the Lord | 1199 | N | — | 0/0+6w | — | 0 | ~señor(adj,1199,8), ~señor(noun,1199,8), señora(noun,1199,2), señorita(noun,157,2), señorito(noun,157,8) | **A** | proper noun — family-less expected |
| 125 | hace | prep | ago (Note: unlike in English, hace precedes the … | 1170 | Y | cog,lit,m+,m-g,yesno | — | — | 0 | — | **A** | function word (prep) — family-less expected |
| 126 | Dios | name | God | 1127 | Y | der,ety,glossary,inh,inh+,yesno | 4/4+76w | 1/1 | 0 | — | **A** | proper noun — family-less expected |
| 127 | sin | prep | without | 1122 | Y | cog,inh | 0/0+24w | — | 0 | — | **A** | function word (prep) — family-less expected |
| 128 | alguien | pron | someone, somebody | 1056 | Y | cog,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (pron) — family-less expected |
| 129 | siempre | adv | always | 1003 | Y | cog,glossary,inh,inh+,yesno | 0/0+8w | — | 2 | siempreviva(noun,0,30), siempreverde(adj,0,1), siempre que(conj,0,1), siempretieso(noun,0,1), siempre jamás(adv,0,1) | **D** | siempreviva/siempreverde (siempre + viva/verde compounds) sit in the DB; no dictionary evidence on this entry |
| 130 | hasta | adv | even | 1000 | Y | cog,der,glossary,inh,inh+,noncog,unc,yesno | — | — | 2 | ~hasta(prep,1000,1), hastag(noun,0,1), hasta luego(phrase,0,1), hastado(adj,0,1), hasta que(conj,0,1) | **A** | homograph of hasta (prep); both entries ineligible (no forms / closed class) so E5 cannot form a family — by design |
| 131 | hasta | prep | until | 1000 | Y | cog,der,glossary,inh,inh+,noncog,unc,yesno | 0/0+59w | — | 0 | ~hasta(adv,1000,1), hastag(noun,0,1), hasta luego(phrase,0,1), hastado(adj,0,1), hasta que(conj,0,1) | **A** | function word (prep) — family-less expected |
| 132 | ahí | adv | there (away from the speaker) | 999 | Y | etymon | 0/0+11w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 133 | ano | noun | anus | 965 | Y | ety | — | 2/2 | 1 | — | **C** | related anal ✓ (ano + -al, real suffixation); substring gate ('anal' ⊅ 'ano') |
| 134 | otro | det | other, another | 872 | Y | cog,glossary,inh,inh+,yesno | 1/1+32w | — | 0 | — | **A** | function word (det) — family-less expected |
| 135 | otro | intj | "Not again!" or "What, again?" (also Otra vez! o… | 872 | Y | cog,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 136 | otro | pron | someone else; another person | 872 | Y | cog,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (pron) — family-less expected |
| 137 | nosotras | pron | we (feminine plural) | 845 | Y | ety | 0/0+1w | 32/26+10w | 0 | nosotres(pron,845,1), nosotros(pron,845,1) | **A** | function word (pron) — family-less expected |
| 138 | nosotres | pron | we | 845 | N | — | — | 33/27+10w | 0 | nosotras(pron,845,1), nosotros(pron,845,1) | **A** | function word (pron) — family-less expected |
| 139 | nosotros | pron | we (masculine plural) | 845 | Y | cog,der,glossary,inh,inh+,yesno | 0/0+1w | 32/26+10w | 0 | nosotras(pron,845,1), nosotres(pron,845,1) | **A** | function word (pron) — family-less expected |
| 140 | Padre | pron | Father (a title for a Latin Catholic priest and … | 829 | N | — | — | — | 0 | ~padre(adj,829,8), ~padre(noun,829,8), padrenuestro(noun,0,1), padrear(verb,0,1), padrejón(noun,0,1) | **A** | function word (pron) — family-less expected |
| 141 | xadre | noun | parent, gender-neutral form of padre or madre | 829 | Y | — | — | — | 1 | — | **C** | prose 'padre + gender-neutral x' — names padre (lemma ✓); prose-only |
| 142 | mira | noun | target | 826 | Y | ety | 1/1+14w | — | 0 | — | **C** | derived mirilla ✓ — substring passes; blocked by rid<=lid ordering + allomorph + root-keys (deverbal-prose entry has no Latin etymons); prose 'Deverbal from mirar' (lemma ✓) |
| 143 | mira | intj | look! | 826 | Y | ety | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 144 | fuera | adv | outside | 736 | Y | cog,etymon,glossary,inh,inh+,lg,yesno | 0/0+24w | 4/4 | 0 | ~fuera(intj,736,1), fueraborda(noun,0,2), fuera de(prep,0,1), fuera de sí(adj,0,1), fuera de onda(adv,0,1) | **C** | related afuera ✓ ('afuera' contains 'fuera', substring passes); source adv has no forms → E4b skipped |
| 145 | fuera | intj | out!, get out! | 736 | Y | cog,etymon,glossary,inh,inh+,lg,yesno | — | — | 0 | ~fuera(adv,736,1), fueraborda(noun,0,2), fuera de(prep,0,1), fuera de sí(adj,0,1), fuera de onda(adv,0,1) | **A** | function word (intj) — family-less expected |
| 146 | después | adv | later, afterwards, afterward, post | 736 | Y | glossary,inh,inh+,yesno | 0/0+6w | 3/3 | 0 | despuntar(verb,0,1), despulpar(verb,0,9), Despuig(name,0,1), despulpe(noun,0,1), después de(prep,0,1) | **C** | related pues ✓ (shared Latin post); substring gate + adv has no forms |
| 147 | desde | prep | since (from a specified time in the past) | 717 | Y | af,der | 0/0+9w | — | 2 | desdén(noun,1,1), desdecir(verb,1,24), Desdémona(name,1,1), desdeñoso(adj,0,3), desdentar(verb,0,1) | **A** | function word (prep) — family-less expected |
| 148 | Claro | name | a male given name | 701 | Y | — | — | — | 0 | ~Claro(name,701,1), ~claro(adj,701,11), ~claro(adv,701,11), ~claro(intj,701,11), ~claro(noun,701,11) | **A** | proper noun — family-less expected |
| 149 | Claro | name | a surname | 701 | Y | — | — | — | 0 | ~Claro(name,701,1), ~claro(adj,701,11), ~claro(adv,701,11), ~claro(intj,701,11), ~claro(noun,701,11) | **A** | proper noun — family-less expected |
| 150 | elles | pron | they; a gender-neutral plural third-person perso… | 696 | N | — | — | 33/27+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 151 | les | article | the (plural) | 696 | Y | -a-o-e,-a-o-x,glossary | — | — | 0 | — | **A** | function word (article) — family-less expected |
| 152 | Estado | name | state (any sovereign polity) | 690 | Y | ety | 0/0+23w | — | 1 | ~estado(noun,690,13), estadounidense(adj,16,9), estadounidense(noun,16,9), estadio(noun,10,2), estadística(noun,5,2) | **A** | proper noun — family-less expected |
| 153 | había | verb | makes pluperfect to verbs as part of the auxilia… | 683 | N | — | — | — | 0 | había una vez(phrase,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 154 | donde | adv | where, in what place | 656 | Y | der | — | — | 0 | ~dónde(adv,1275,1), ~dónde(noun,1275,2), ~donde(conj,656,1), ~donde(prep,656,1), ~donde(pron,656,1) | **A** | all four donde entries share the Latin etymon unde and merge in-graph, but a component with no eligible head is not formed into a family — by design; function-word homographs |
| 155 | donde | conj | because | 656 | Y | der | — | — | 0 | ~dónde(adv,1275,1), ~dónde(noun,1275,2), ~donde(adv,656,1), ~donde(prep,656,1), ~donde(pron,656,1) | **A** | function word; same-etymon homographs cannot form a family without an eligible head |
| 156 | donde | prep | by, near to | 656 | Y | der | — | — | 0 | ~dónde(adv,1275,1), ~dónde(noun,1275,2), ~donde(adv,656,1), ~donde(conj,656,1), ~donde(pron,656,1) | **A** | function word; same as the other donde entries |
| 157 | donde | pron | where, in what place | 656 | Y | der | 2/2+4w | 1/1 | 0 | ~dónde(adv,1275,1), ~dónde(noun,1275,2), ~donde(adv,656,1), ~donde(conj,656,1), ~donde(prep,656,1) | **A** | function word; same as the other donde entries |
| 158 | Podemos | name | a Spanish left wing political party | 644 | N | — | 4/4 | — | 0 | podemita(adj,0,1), podemita(noun,0,1), podemista(adj,0,1), podemista(noun,0,1), podemizar(verb,0,2) | **A** | proper noun — family-less expected |
| 159 | Nuevo | name | a surname | 638 | N | — | — | — | 0 | ~nuevo(adj,638,6), Nuevo León(name,0,1), nuevo rico(noun,0,1), Nuevo Mundo(name,0,1), nuevo tango(noun,0,1) | **A** | proper noun — family-less expected |
| 160 | hija | noun | daughter; female equivalent of hijo | 633 | Y | glossary,inh,inh+,yesno | 0/0+5w | 1/1 | 0 | — | **C** | related hijo ✓ (gender pair of one lexeme); substring gate ('hija' ⊅ 'hijo') |
| 161 | hije | noun | child (offspring) | 633 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 162 | allí | adv | there (away from the speaker and the listener) | 631 | Y | compound,glossary,inh,inh+,yesno | 0/0+3w | — | 1 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 163 | Amigo | name | a surname | 610 | Y | — | — | — | 0 | ~amigo(intj,610,13), ~amigo(noun,610,13), amigote(noun,0,13), amigovio(noun,0,1), amigo secreto(noun,0,1) | **A** | proper noun — family-less expected |
| 164 | amigue | noun | friend | 610 | Y | af | — | — | 1 | amiguita(noun,9,1), amiguito(noun,9,13), amiguete(noun,0,13), amiguismo(noun,0,13), amigui(noun,0,1) | **C** | af template carries only the suffix -e; the base amigo/amiga appears in prose only ('From amigo and amiga…'); bases exist as lemmas (family of 13) |
| 165 | amigx | noun | gender-neutral neologism for amigo and amiga (“f… | 610 | N | — | — | — | 1 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 166 | nuestro | pron | ours | 600 | Y | glossary,inh,inh+,yesno | — | 19/8 | 0 | ~nuestro(det,600,1), nuestro mar(noun,0,1), Nuestra Señora(name,0,1), nuestros primeros pad…(noun,0,1) | **A** | function word (pron) — family-less expected |
| 167 | nuestro | det | our, ours, to us | 600 | Y | glossary,inh,inh+,yesno | 0/0+2w | 25/12 | 0 | ~nuestro(pron,600,1), nuestro mar(noun,0,1), Nuestra Señora(name,0,1), nuestros primeros pad…(noun,0,1) | **A** | function word (det) — family-less expected |
| 168 | luego | adv | then (afterward) | 581 | Y | cog,der,doublet,etymon,glossary,inh,inh+,root, | — | — | 5 | ~luego(conj,581,1), luego de(prep,0,1), luego que(conj,0,1), luego luego(adv,0,1) | **C** | doublet template names locus (lemma ✓) — never loaded |
| 169 | luego | conj | therefore (consequently) | 581 | Y | cog,der,doublet,etymon,glossary,inh,inh+,root, | 0/0+8w | 2/2 | 1 | ~luego(adv,581,1), luego de(prep,0,1), luego que(conj,0,1), luego luego(adv,0,1) | **A** | function word (conj) — family-less expected |
| 170 | hoy | adv | today, tonight (on the current day) | 568 | Y | ,,cog,glossary,inh,inh+,lg,yesno | 0/0+19w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 171 | tres | num | three | 566 | Y | ety,glossary,inh,inh+,yesno | 0/0+19w | 6/5 | 0 | — | **A** | function word (num) — family-less expected |
| 172 | necesitar | verb | to need | 561 | Y | cog,etymon | — | 3/3 | 2 | necesario(adj,99,3), necesidad(noun,44,1), necesariamente(adv,11,3), necesitado(adj,5,1), neceser(noun,0,1) | **C** | related necesario/necesidad/necesitado ✓; substring gate |
| 173 | dije | noun | adorns, locket | 557 | Y | — | — | — | 2 | — | **C** | prose 'Derived from dije (I said), an inflection of the verb decir' — names decir (lemma ✓); prose-only |
| 174 | dije | adj | pleasant, nice, likable (of a person) | 557 | Y | — | — | — | 2 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 175 | oye | intj | hey! listen! (call to attract attention of a sin… | 554 | Y | ety | — | — | 6 | — | **A** | function word (intj) — family-less expected |
| 176 | conmigo | adv | with me | 530 | Y | glossary,inh,inh+,yesno | — | — | 0 | conmiseración(noun,0,1), conminar(verb,0,2), conminación(noun,0,1), conmisto(adj,0,2), conmixto(adj,0,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 177 | aún | adv | still, yet | 508 | Y | ety | — | 1/1 | 2 | — | **C** | related aun ✓ — accent-variant pair of one lexeme; RAW-case substring gate ('aun' ⊄ 'aún') and no-forms source keep them apart |
| 178 | mío | pron | mine; of mine | 501 | Y | der,inh | — | 19/8 | 0 | — | **A** | function word (pron) — family-less expected |
| 179 | mío | det | mine, my; of mine | 501 | Y | der,inh | 1/1+1w | 25/12 | 0 | — | **A** | function word (det) — family-less expected |
| 180 | cada | det | each; every | 495 | Y | der,glossary,inh,inh+,yesno | 0/0+23w | — | 0 | — | **A** | function word (det) — family-less expected |
| 181 | cada | adv | every time | 495 | Y | der,glossary,inh,inh+,yesno | — | — | 1 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 182 | contigo | adv | with you (singular) | 478 | Y | der | — | — | 0 | continuar(verb,40,5), continuación(noun,18,1), continuo(adj,12,6), continente(noun,7,7), continuamente(adv,6,6) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 183 | hemo | noun | heme | 473 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 184 | alguno | det | some, any | 468 | Y | cog,der,glossary,inh,inh+,yesno | 0/0+8w | — | 0 | ~alguno(pron,468,1), algún día(adv,0,1), alguna vez(adv,0,1), alguna cosa(pron,0,1), algún tanto(adv,0,1) | **A** | function word (det) — family-less expected |
| 185 | alguno | pron | someone | 468 | Y | cog,der,glossary,inh,inh+,yesno | — | — | 2 | ~alguno(det,468,1), algún día(adv,0,1), alguna vez(adv,0,1), alguna cosa(pron,0,1), algún tanto(adv,0,1) | **A** | function word (pron) — family-less expected |
| 186 | veces | prep | by, times (multiplication) | 462 | N | — | — | — | 1 | — | **A** | function word (prep) — family-less expected |
| 187 | eh | intj | hey! (used to call, draw attention, warn or repr… | 457 | N | — | — | 3/3 | 5 | — | **A** | function word (intj) — family-less expected |
| 188 | quien | pron | who | 442 | Y | der,glossary,inh,inh+,yesno | 0/0+3w | — | 1 | ~quién(pron,1338,1), quiénes(pron,54,1), quienquiera(pron,10,17), quién va(phrase,0,1), quienquita(intj,0,1) | **A** | function word (pron) — family-less expected |
| 189 | Amor | name | a surname | 431 | Y | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 190 | entre | prep | between | 428 | Y | glossary,inh,inh+,yesno | 2/2+34w | — | 1 | entrenador(noun,39,6), entrever(verb,35,27), entrevista(noun,35,27), entrevistar(verb,35,27), entrenamiento(noun,31,6) | **A** | function word (prep) — family-less expected |
| 191 | ve | noun | The name of the Latin script letter V/v. | 424 | Y | — | 0/0+5w | — | 2 | — | **B** | letter-name entry; only a 'See v.' pointer — no etymology at all |
| 192 | chicx | noun | child | 409 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 193 | chique | noun | a young person | 409 | N | — | — | — | 0 | chiquillo(noun,3,19), chiquita(noun,3,1), chiquito(adj,3,19), chiquito(noun,3,19), chiquero(noun,1,2) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 194 | haz | noun | face | 394 | Y | doublet,etymon,glossary,inh,inh+,yesno | 0/0+1w | — | 3 | — | **C** | doublet template names facies/faz (lemmas ✓) — never loaded |
| 195 | todavía | adv | still, yet | 394 | Y | cog,ety | — | — | 2 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 196 | unos | det | about, approximately | 384 | Y | inh | — | — | 0 | — | **A** | function word (det) — family-less expected |
| 197 | hermana | noun | sister; female equivalent of hermano (“brother”) | 377 | Y | ety,glossary,inh,inh+,yesno | 1/0+3w | 1/1 | 0 | hermane(noun,377,1), hermano(noun,377,4), hermanar(verb,377,4), hermandad(noun,8,2), hermandad(verb,8,2) | **D** | relatives exist in the DB but this entry's own evidence does not connect them |
| 198 | hermane | noun | sibling | 377 | Y | af | — | — | 0 | hermana(noun,377,1), hermano(noun,377,4), hermanar(verb,377,4), hermandad(noun,8,2), hermandad(verb,8,2) | **C** | prose 'From hermano' (lemma ✓); gender-neutral neologism |
| 199 | Cabeza | name | a surname | 369 | N | — | — | — | 0 | ~cabeza(noun,369,20), ~cabeza(noun,369,20), cabezota(adj,3,20), cabezón(adj,1,20), cabezón(noun,1,20) | **A** | proper noun — family-less expected |
| 200 | Cariño | name | a municipality of A Coruña, Spain | 362 | Y | ety | — | — | 0 | ~cariño(noun,362,4), cariñoso(adj,4,4), cariñosa(noun,3,1), Carina(name,2,1), cariñosamente(adv,1,4) | **A** | proper noun — family-less expected |
| 201 | digo | intj | I mean; used to explain or correct a previous ut… | 362 | Y | der | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 202 | van | noun | van (vehicle) | 362 | Y | ety | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 203 | buenas | intj | hello, good morning, good afternoon, good evenin… | 358 | Y | ellipsis | — | 0/0+1w | 1 | buena(noun,563,16), Buenaventura(name,0,1), Buenaventura(name,0,1), buenaventura(noun,0,9), buenazo(adj,0,15) | **A** | function word (intj) — family-less expected |
| 204 | somo | noun | summit; peak | 357 | Y | der | — | — | 3 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 205 | primera | noun | first gear (lowest gear in a motor vehicle) | 343 | Y | der | 0/0+1w | — | 0 | primero(adj,343,6), primero(adv,310,6), primero(noun,310,6), prime(noun,2,1), primeramente(adv,1,6) | **C** | prose 'From primero' (lemma ✓) — substantivized feminine of primero |
| 206 | CHICO | name | Cámara Hondureña de la Industria de la Construcc… | 343 | N | — | — | — | 0 | ~chico(adj,409,19), ~chico(noun,409,19), ~chico(noun,402,19), chicote(noun,0,19), chicote(noun,0,19) | **A** | proper noun — family-less expected |
| 207 | pues | conj | so, then; in that case | 340 | Y | cog,inh | 0/0+2w | 1/1 | 1 | — | **A** | function word (conj) — family-less expected |
| 208 | adiós | intj | goodbye, farewell | 339 | Y | cog,compound,der | 1/0+3w | 5/2+5w | 0 | ~adiós(noun,339,1), ~adios(intj,23,1), adiós cará(intj,0,1), adiós mis flores(intj,0,1), adiós Madrid, que te …(phrase,0,1) | **A** | function word (intj) — family-less expected |
| 209 | adiós | noun | farewell; goodbye | 339 | Y | cog,compound,der | — | — | 0 | ~adiós(intj,339,1), ~adios(intj,23,1), adiós cará(intj,0,1), adiós mis flores(intj,0,1), adiós Madrid, que te …(phrase,0,1) | **C** | compound template a + Dios; base Dios is a name-pos lemma (ineligible as E1 parent) |
| 210 | quizá | adv | perhaps, maybe | 333 | Y | cog,glossary,inh,inh+,yesno | 0/0+1w | 1/0 | 3 | quizá y sin quizá(prep_phrase,0,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 211 | durante | prep | during, in, over | 331 | Y | der | — | — | 0 | Durán(name,1,1), Durán(name,1,1), Durango(name,0,1), duranta(noun,0,1), duranguense(adj,0,2) | **A** | function word (prep) — family-less expected |
| 212 | cuál | det | what; which | 322 | Y | etymon,glossary,inh,inh+,yesno | — | — | 1 | — | **A** | function word (det) — family-less expected |
| 213 | cuál | pron | which one, what, which | 322 | Y | etymon,glossary,inh,inh+,yesno | — | 2/2 | 0 | — | **A** | function word (pron) — family-less expected |
| 214 | historiar | verb | to depict (history), write down a history | 321 | N | — | — | — | 0 | historia(noun,321,14), historial(noun,16,14), histórico(adj,6,12), histórico(noun,6,12), historieta(noun,2,14) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 215 | Nueva | name | a village in northeastern Asturias, Spain | 318 | N | — | — | — | 0 | ~nueva(noun,318,2), nuevamente(adv,24,6), Nueva Roma(name,0,1), Nueva York(name,0,1), nuevaolero(adj,0,1) | **A** | proper noun — family-less expected |
| 216 | dentrar | verb | to enter, go in | 316 | Y | prothetic form,surf | — | — | 0 | dentro(adv,316,1), dentrada(noun,0,1), dentro de(prep,0,1), dentrotraer(verb,0,15) | **C** | 'prothetic form' template names entrar (lemma ✓) + 'surf' template 'dentro + -ar' names dentro (lemma ✓); neither template type is parsed |
| 217 | dentro | adv | inside (for space) | 316 | Y | ety | 1/1+2w | — | 0 | dentrar(verb,316,1), dentrada(noun,0,1), dentro de(prep,0,1), dentrotraer(verb,0,15) | **C** | derived adentro ✓; source adv has no forms → E4/E4b skipped |
| 218 | casi | adv | almost | 316 | Y | dbt,slbor | 0/0+3w | 1/0 | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 219 | Puerta | name | a surname | 315 | N | — | — | — | 0 | ~puerta(noun,315,19), Puerto(name,25,1), puerto(noun,25,12), puertorriqueño(adj,1,1), puertorriqueño(noun,1,1) | **A** | proper noun — family-less expected |
| 220 | hacia | prep | toward, towards | 307 | Y | cog,der,inh,noncog | 0/0+5w | — | 0 | hacia abajo(adv,0,1), hacia atrás(adv,0,1), hacia arriba(adv,0,1) | **A** | function word (prep) — family-less expected |
| 221 | Año | name | a surname | 305 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 222 | niñe | noun | child | 304 | Y | af | — | — | 0 | — | **C** | af template niña + -e; base niña lemma ✓; suffix -e is in E1's inflectional-desinence reject list (…,a,e,o,…) |
| 223 | tíe | noun | uncle or aunt | 302 | Y | af | — | — | 0 | — | **C** | prose 'From tío' (lemma ✓) |
| 224 | os | pron | you, to you, for you; dative and accusative of v… | 290 | Y | glossary,inh,inh+,yesno | — | 32/26+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 225 | ox | intj | shoo | 290 | Y | bor+ | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 226 | ey | intj | hey! | 289 | Y | ety | — | 3/3 | 1 | — | **A** | function word (intj) — family-less expected |
| 227 | hey | intj | hey! | 289 | Y | ety | — | 3/3 | 6 | — | **A** | function word (intj) — family-less expected |
| 228 | deja | noun | rest (that remaining after cutting textiles) | 284 | Y | ety | — | — | 0 | — | **C** | prose 'Deverbal from dejar' (lemma ✓) |
| 229 | Justo | name | a male given name, equivalent to English Justus | 277 | N | — | — | 4/3 | 0 | ~justo(adj,277,18), ~justo(adv,277,18), justofué(noun,0,1), justojuez(noun,0,1), justo a tiempo(adv,0,1) | **A** | proper noun — family-less expected |
| 230 | venga | intj | A cheer or expression of support, encouragement,… | 270 | N | — | — | — | 0 | vengar(verb,270,6), venganza(noun,38,6), vengador(noun,3,6), vengativo(adj,1,6), vengativamente(adv,0,6) | **A** | function word (intj) — family-less expected |
| 231 | manar | verb | to gush forth | 266 | Y | der | — | 2/2 | 0 | — | **C** | related emanar/manantial ✓; substring gate |
| 232 | ninguno | det | no; none | 265 | Y | cog,glossary,inh,inh+,surf,yesno | — | 1/0 | 0 | ~ninguno(pron,265,1), ningunear(verb,0,1), ninguneo(noun,0,1), ningufoneo(noun,0,1), ningún nacido(noun,0,1) | **A** | function word (det) — family-less expected |
| 233 | ninguno | pron | nobody; no one | 265 | Y | cog,glossary,inh,inh+,surf,yesno | — | — | 1 | ~ninguno(det,265,1), ningunear(verb,0,1), ninguneo(noun,0,1), ningufoneo(noun,0,1), ningún nacido(noun,0,1) | **A** | function word (pron) — family-less expected |
| 234 | escucha | noun | listening | 253 | Y | ety | 0/0+1w | — | 0 | ~escucha(noun,253,1), escuchar(verb,253,4), escucho(verb,34,1), escuchador(adj,0,4), escuchador(noun,0,4) | **C** | prose 'Deverbal from escuchar' (lemma ✓, family of 4) |
| 235 | escucha | noun | scout | 253 | Y | ety | 0/0+1w | — | 0 | ~escucha(noun,253,1), escuchar(verb,253,4), escucho(verb,34,1), escuchador(adj,0,4), escuchador(noun,0,4) | **C** | prose 'Deverbal from escuchar' (lemma ✓, family of 4) |
| 236 | puntar | verb | to point, to mark with points | 253 | Y | — | — | 3/3 | 0 | punta(noun,21,38), puntaje(noun,2,38), puntada(noun,1,1), puntapié(noun,1,9), puntal(noun,0,38) | **C** | related apuntar/punto/puntuar ✓ (etymology text: 'From punto'); substring gate |
| 237 | haya | noun | beech, beech tree | 252 | Y | cog,glossary,inh,inh+,yesno | 2/1+3w | — | 0 | — | **C** | derived hayedo ✓ (haya + -edo); E4 root-key gate (target has no Latin etyma) |
| 238 | Grande | name | a surname | 251 | Y | — | — | — | 0 | ~grande(adj,609,12), ~grande(noun,609,12), grandioso(adj,37,3), grandeza(noun,6,12), grandote(adj,5,12) | **A** | proper noun — family-less expected |
| 239 | aunque | conj | though, although, even though, albeit | 247 | Y | ety | 0/0+2w | — | 3 | aunque más(conj,0,1), aunque la mona se vis…(proverb,0,1) | **A** | function word (conj) — family-less expected |
| 240 | ma | noun | mum; mom | 244 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 241 | mas | conj | but | 244 | Y | doublet,glossary,inh,inh+,yesno | — | — | 4 | — | **A** | function word (conj) — family-less expected |
| 242 | toma | noun | conquest, capture, taking, takeover | 243 | Y | ety | 0/0+5w | — | 5 | — | **C** | prose 'Deverbal from tomar' (lemma ✓) |
| 243 | allá | adv | there, over there, thither, yonder (in a directi… | 242 | Y | compound,glossary,inh,inh+,yesno | 0/0+4w | — | 1 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 244 | arriba | adv | above, over | 242 | Y | glossary,inh,inh+,yesno | 0/0+11w | 3/3 | 2 | ~arriba(intj,242,1), arribar(verb,242,2), arribo(noun,1,1), arribista(noun,0,1), arribismo(noun,0,1) | **C** | related riba/ribera/ribero ✓ ('arriba' contains 'riba', substring passes); source adv has no forms |
| 245 | arriba | intj | come on! | 242 | Y | glossary,inh,inh+,yesno | — | — | 0 | ~arriba(adv,242,1), arribar(verb,242,2), arribo(noun,1,1), arribista(noun,0,1), arribismo(noun,0,1) | **A** | function word (intj) — family-less expected |
| 246 | Guerra | name | a surname | 241 | Y | — | — | — | 0 | ~guerra(noun,241,22), Guerrero(name,17,1), Guerrero(name,17,1), guerrero(adj,17,22), guerrero(noun,17,22) | **A** | proper noun — family-less expected |
| 247 | Mujeres | name | a surname | 235 | Y | — | — | — | 0 | mujer(noun,590,13), mujeriego(adj,3,13), mujeriego(noun,3,13), mujerzuela(noun,2,13), mujercita(noun,2,13) | **A** | proper noun — family-less expected |
| 248 | Vuelta | name | the Vuelta a España | 235 | N | — | — | — | 1 | ~vuelta(noun,235,20), vuelto(noun,235,20), vueltas(noun,31,1), vueltero(adj,0,20), vueltabajero(adj,0,2) | **A** | proper noun — family-less expected |
| 249 | oportunidad | noun | opportunity, chance, shot, break, occasion, time… | 225 | Y | der | — | — | 0 | oportuno(adj,6,7), Oporto(name,2,1), oporto(noun,2,1), oportunista(adj,1,7), oportunista(noun,1,7) | **D** | oportuno/oportunista sit in the DB sharing the stem oportun-; no dictionary evidence on this entry |
| 250 | listar | verb | to register, enter in a list | 224 | Y | — | — | — | 0 | lista(noun,203,7), listado(adj,2,1), listado(noun,2,1), lista negra(noun,0,1), lista al Senado(noun,0,1) | **C** | prose 'From lista' (lemma ✓) |
| 251 | vetar | verb | to veto | 222 | Y | der,doublet | — | 2/2 | 0 | — | **C** | doublet vedar ✓ + related veto ✓ — doublet never loaded; related substring-gated |
| 252 | auto | noun | a public deed or ceremony | 221 | Y | bor,doublet | 0/0+1w | — | 0 | — | **C** | doublet template names acto (lemma ✓) — never loaded |
| 253 | OK | adj | OK | 218 | Y | ety | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 254 | OK | intj | OK | 218 | Y | ety | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 255 | mesar | verb | to pull out; to tear out (hair) | 217 | Y | der,dercat,inh | — | 1/1 | 0 | — | **A** | from Latin metere; related atusar is semantically adjacent (hair) but not derived |
| 256 | ello | pron | it, neuter third-person subject and disjunctive … | 212 | Y | glossary,inh,inh+,yesno | 0/0+2w | 33/27+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 257 | ello | noun | (Freud's concept of) id | 212 | Y | glossary,inh,inh+,yesno | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 258 | pregunta | noun | question (sentence that asks for information) | 212 | Y | ety | 1/0+5w | — | 0 | preguntar(verb,212,4), preguerra(noun,0,22), preguntón(adj,0,4), pregustar(verb,0,12), preguntador(adj,0,4) | **C** | prose 'Deverbal from preguntar' (lemma ✓, family of 4) |
| 259 | bebé | noun | baby | 209 | Y | bor+,ux | 10/1+1w | — | 11 | — | **C** | derived portabebés ✓ (compound); E4 root-key gate — French etymon, no Latin roots on source |
| 260 | Segundo | name | a male given name | 208 | Y | — | 0/0+1w | — | 0 | ~segundo(adj,208,10), ~segundo(noun,208,10), segundar(verb,208,1), segunda(noun,88,1), según(prep,87,1) | **A** | proper noun — family-less expected |
| 261 | segundar | verb | to repeat an action, do again | 208 | N | — | — | — | 0 | Segundo(name,208,1), segundo(adj,208,10), segundo(noun,208,10), segunda(noun,88,1), según(prep,87,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 262 | comido | adj | having had lunch; having already eaten | 207 | N | — | — | — | 0 | comida(noun,207,2), comidilla(noun,0,2), comidería(noun,0,1), comida basura(noun,0,1), comida rápida(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 263 | llamar al pan, pan, y al vino, vino | verb | to call a spade a spade | 204 | Y | lit,m-g,yesno | — | 0/0+1w | 0 | llama(noun,243,5), llama(noun,243,5), llamar(verb,243,10), llamado(adj,155,10), llamado(noun,155,10) | **A** | multi-word expression — family-less expected |
| 264 | trata | noun | trafficking, trade, slave trade | 198 | Y | ety | — | — | 0 | tratar(verb,198,6), tratamiento(noun,30,6), tratado(noun,30,3), tratable(adj,1,6), tratante(noun,0,6) | **C** | prose 'Deverbal from tratar' (lemma ✓, family of 6) |
| 265 | tampoco | adv | neither; nor; also not | 197 | Y | ety | — | — | 0 | tampón(noun,2,2), tamponar(verb,2,2), tamponamiento(noun,0,1), tampografía(noun,0,1) | **C** | etymology tree lists Spanish tan and Spanish poco (both lemmas ✓) and prose 'Univerbation of tan + poco'; Spanish tree-ancestors are parsed but never used to link |
| 266 | ama | noun | lady of the house | 196 | Y | ety,glossary,inh,inh+,yesno | 0/0+7w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 267 | amo | noun | master (man who owns a slave) | 196 | Y | back-form,ety | 0/0+2w | — | 0 | — | **C** | back-form template 'Back-formation from ama' names ama (lemma ✓); back-form template type is not parsed |
| 268 | Joven | name | a surname | 196 | Y | — | — | — | 0 | ~joven(adj,196,6), ~joven(noun,196,6), jovenzuelo(noun,0,6), Jovenlandia(name,0,6), jovenlandés(noun,0,1) | **A** | proper noun — family-less expected |
| 269 | Sola | name | a surname | 194 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 270 | mediar | verb | to mediate | 190 | Y | bor+,der | — | 3/3 | 0 | Media(name,94,1), media(noun,94,8), medianoche(noun,26,1), medias(noun,17,1), mediante(prep,9,1) | **C** | related mediación/mediador/medio ✓; substring gate |
| 271 | Segura | name | Segura (river) | 188 | N | — | — | — | 0 | seguro(adj,655,9), seguro(adv,655,9), seguro(noun,655,9), seguridad(noun,181,4), seguramente(adv,52,9) | **A** | proper noun — family-less expected |
| 272 | seis | num | six | 182 | Y | cog,ety,glossary,inh,inh+,yesno | — | — | 0 | — | **A** | function word (num) — family-less expected |
| 273 | ademar | verb | to encase | 178 | Y | ety | — | — | 0 | además(adv,178,1), adema(noun,6,1), ademán(noun,0,1), además de(prep,0,1) | **A** | prose base ademe is not a lemma in the DB — evidence unusable |
| 274 | además | adv | in addition, moreover, furthermore, further, als… | 178 | Y | cog,univerbation | 0/0+1w | — | 8 | ademar(verb,178,1), adema(noun,6,1), ademán(noun,0,1), además de(prep,0,1) | **C** | univerbation template a + demás; base demás adj has no form records (ineligible E1 parent) |
| 275 | recuerdo | noun | memory (a specific thing that is remembered) | 176 | Y | ety | — | — | 1 | recuento(noun,4,1) | **C** | prose 'Deverbal from recordar' (lemma ✓) |
| 276 | acerca | adv | adjacent | 175 | Y | ety | 0/0+1w | 2/2 | 0 | acercar(verb,175,11), acercamiento(noun,3,11), acerca de(prep,0,1), acercador(adj,0,11), acercante(adj,0,11) | **C** | related acercar ✓ ('acercar' contains 'acerca', substring passes) + cerca ✓; source adv has no forms |
| 277 | Luz | name | a female given name | 175 | Y | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 278 | demonios | adv | the hell, on earth (for emphasis after a questio… | 174 | N | — | — | — | 1 | demonio(noun,174,5), demoníaco(adj,1,1), demonizar(verb,0,5), demonología(noun,0,1), demonólogo(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 279 | Paz | name | a female given name | 170 | Y | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 280 | dado | noun | a die or dice | 168 | Y | cog,der,inh | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 281 | dado | prep | given, considering | 168 | Y | glossary,inh,inh+,yesno | 0/0+1w | — | 0 | — | **A** | function word (prep) — family-less expected |
| 282 | vivar | verb | to applaud | 166 | Y | — | — | — | 1 | vivaracho(adj,0,1), ~Vivar(name,0,1), vivario(noun,0,1), vivariense(adj,0,1), vivariense(noun,0,1) | **D** | transparent vivar ← viva (¡viva!); no dictionary evidence on this entry |
| 283 | diga | intj | way to say hello on the telephone | 163 | Y | — | — | — | 4 | — | **A** | function word (intj) — family-less expected |
| 284 | anoche | adv | last night | 163 | Y | cog,glossary,inh,inh+,yesno | 1/1+1w | 1/1 | 1 | anochecer(noun,5,2), anochecer(verb,5,2), anochecida(noun,0,1) | **C** | derived anteanoche ✓ + related noche ✓; source adv has no forms |
| 285 | Rey | name | a surname | 160 | Y | — | — | 1/1 | 0 | — | **A** | proper noun — family-less expected |
| 286 | Rey | name | a male given name | 160 | Y | — | — | 1/1 | 0 | — | **A** | proper noun — family-less expected |
| 287 | diablos | intj | damn it, hell, heck | 159 | Y | — | — | — | 0 | diablo(noun,159,6), ~diablos(adv,159,1), Diablo(name,68,1), diablito(noun,0,6), diablesa(noun,0,6) | **A** | function word (intj) — family-less expected |
| 288 | diablos | adv | the hell | 159 | Y | — | 0/0+1w | — | 1 | diablo(noun,159,6), ~diablos(intj,159,1), Diablo(name,68,1), diablito(noun,0,6), diablesa(noun,0,6) | **D** | same-word entry in another family; no usable link evidence here |
| 289 | Diez | name | a surname | 157 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 290 | Calle | name | a surname | 153 | Y | — | — | — | 0 | ~calle(noun,153,16), callejón(noun,17,16), callejero(adj,4,16), callejero(noun,4,16), callejuela(noun,0,16) | **A** | proper noun — family-less expected |
| 291 | prueba | noun | proof; evidence (usually in the plural) | 153 | Y | der,deverbal,ety,inh | 0/0+26w | 1/1 | 3 | prueba de vida(noun,0,1), prueba y error(noun,0,1), prueba de fuego(noun,0,1), prueba de choque(noun,0,1), prueba del fuego(noun,0,1) | **C** | deverbal template → base probar (lemma ✓) with EMPTY affix — E1 skips empty-affix edges; related probar also listed |
| 292 | mía | noun | a regiment of 100 soldiers in the Spanish protec… | 152 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 293 | afuera | adv | out, outside | 150 | Y | af,cog,glossary,inh,inh+,root,yesno | 2/2+2w | 1/1 | 0 | ~afuera(intj,150,1), afueras(noun,10,1), afuerino(adj,0,1), afuerita(adv,0,1), afuerear(verb,0,1) | **C** | af template a- + fuera; base fuera adv carries no forms (ineligible E1 parent); derived afuerino/afuerita ✓ + related afueras ✓ |
| 294 | afuera | intj | get out! | 150 | Y | af,cog,glossary,inh,inh+,root,yesno | — | — | 0 | ~afuera(adv,150,1), afueras(noun,10,1), afuerino(adj,0,1), afuerita(adv,0,1), afuerear(verb,0,1) | **A** | function word (intj) — family-less expected |
| 295 | detrás | adv | behind, at the rear | 148 | Y | ety | — | 1/1+2w | 0 | ~detrás(prep,148,1), detractor(noun,0,1), detraer(verb,0,15), detracción(noun,0,1), detrás de(prep,0,1) | **C** | related atrás ✓ (morphological sibling, de+tras / a+tras); substring gate ('atrás' ⊅ 'detrás') |
| 296 | detrás | prep | behind (used with possessive pronouns) | 148 | Y | ety | — | — | 1 | ~detrás(adv,148,1), detractor(noun,0,1), detraer(verb,0,15), detracción(noun,0,1), detrás de(prep,0,1) | **A** | function word (prep) — family-less expected |
| 297 | querida | noun | dear, honey, darling | 148 | Y | — | — | — | 0 | querido(adj,148,1), querido(noun,148,1), queriendo(adv,9,1), querible(adj,0,17), querindongo(noun,0,1) | **C** | prose 'From querer' (lemma ✓) |
| 298 | querido | adj | dear (also used in letter introductions, etc.) | 148 | Y | — | 0/0+2w | — | 1 | querida(noun,148,1), ~querido(noun,148,1), queriendo(adv,9,1), querible(adj,0,17), querindongo(noun,0,1) | **C** | prose 'Past participle of querer' (lemma ✓) |
| 299 | querido | noun | sweetheart | 148 | Y | — | — | — | 0 | querida(noun,148,1), ~querido(adj,148,1), queriendo(adv,9,1), querible(adj,0,17), querindongo(noun,0,1) | **C** | prose 'Past participle of querer' (lemma ✓) |
| 300 | LIBRE | name | Liberalismo Renovador | 147 | N | — | — | — | 0 | ~libre(adj,147,2), libremente(adv,6,2), librería(noun,5,10), libreta(noun,4,10), libreto(noun,1,2) | **A** | proper noun — family-less expected |
| 301 | cambio | intj | over | 147 | Y | ,,cog,ety | — | — | 0 | ~cambio(noun,147,5), cambiar(verb,147,7), cambiado(adj,81,1), cambiante(adj,1,7), cambiante(noun,1,7) | **A** | function word (intj) — family-less expected |
| 302 | restar | verb | to subtract, to reduce, to deduct | 146 | Y | bor+ | 0/0+1w | 3/3 | 5 | restaurante(noun,55,2), restaurar(verb,4,1), restante(adj,3,1), restante(noun,3,1), restauración(noun,2,1) | **C** | related restante/resto ✓ (real deverbals); substring + allomorph gates |
| 303 | trato | noun | treatment (the process or manner of treating som… | 140 | Y | ety | 0/0+8w | 6/6 | 5 | trato hecho(phrase,0,1) | **C** | ety template 'Deverbal from tratar' (lemma ✓, family of 6) + related trata/tratable/tratadista/tratado/tratamiento/tratar ✓; deverbal-prose not parsed; substring gates |
| 304 | Perfecto | name | a male given name | 140 | N | — | — | — | 0 | ~perfecto(adj,140,5), perfectamente(adv,43,5), perfección(noun,8,6), perfeccionar(verb,1,6), perfect(adj,1,2) | **A** | proper noun — family-less expected |
| 305 | demás | adj | other, remaining | 139 | Y | af,cog,glossary,inh,inh+,yesno | 2/2+5w | 2/2 | 0 | demasiado(adj,432,4), demasiado(adv,432,4), ~demás(adv,139,1), ~demás(pron,139,1), demasía(noun,0,4) | **C** | af template de- + más; base más is in _FUNC_STOPLIST (ineligible E1 parent); derived además/demasiado ✓ also listed |
| 306 | demás | adv | besides, in addition to | 139 | Y | af,cog,glossary,inh,inh+,yesno | — | — | 1 | demasiado(adj,432,4), demasiado(adv,432,4), ~demás(adj,139,1), ~demás(pron,139,1), demasía(noun,0,4) | **C** | af template de- + más; base más in _FUNC_STOPLIST |
| 307 | demás | pron | others, other ones | 139 | Y | af,cog,glossary,inh,inh+,yesno | — | — | 0 | demasiado(adj,432,4), demasiado(adv,432,4), ~demás(adj,139,1), ~demás(adv,139,1), demasía(noun,0,4) | **A** | function word (pron) — family-less expected |
| 308 | sexar | verb | to sex (determine the sex of) | 135 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 309 | acabo | noun | synonym of acabamiento | 134 | Y | ety | — | — | 1 | acabose(noun,0,1) | **C** | prose 'Deverbal from acabar' (lemma ✓) despite synonym-redirect gloss |
| 310 | encima | adv | on top of something | 133 | Y | ety | 1/1+8w | — | 1 | ~encima(prep,133,1), encimar(verb,133,1), encimera(noun,1,1), encimoso(adj,0,1), encima de(prep,0,1) | **C** | derived encimera ✓; E4 source eligibility requires form records — adverbs without forms are skipped |
| 311 | encima | prep | on top of, (loosely) above | 133 | Y | ety | — | — | 2 | ~encima(adv,133,1), encimar(verb,133,1), encimera(noun,1,1), encimoso(adj,0,1), encima de(prep,0,1) | **A** | function word (prep) — family-less expected |
| 312 | encimar | verb | to put up; to store high up | 133 | Y | ety | — | — | 0 | encima(adv,133,1), encima(prep,133,1), encimera(noun,1,1), encimoso(adj,0,1), encima de(prep,0,1) | **C** | suffix template encima + -ar; base encima adv carries no forms (ineligible E1 parent) |
| 313 | uh | intj | used to express disappointment or disdain | 132 | N | — | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 314 | cállate | intj | shut up! | 132 | N | — | — | — | 0 | callar(verb,153,6), callado(adj,13,6), callao(noun,3,1), calladamente(adv,0,6), Callao(name,0,1) | **A** | function word (intj) — family-less expected |
| 315 | suceder | verb | to happen, to befall, to occur | 131 | Y | der | — | 1/1 | 2 | sucedáneo(adj,0,2), sucedáneo(noun,0,2) | **C** | related suceso ✓; substring gate |
| 316 | siguiente | adj | following | 131 | Y | der,glossary,inh,inh+,yesno | — | 2/2+3w | 0 | sigüís(noun,0,1), siguiriya(noun,0,1) | **C** | related seguir/seguidor ✓ (old present participle of seguir); substring gate |
| 317 | sino | noun | destiny, fate, lot | 130 | Y | bor+,cog,doublet | — | — | 4 | — | **C** | doublet template names signo (lemma ✓) — never loaded |
| 318 | sino | conj | but (rather) (after a negative clause) | 130 | Y | cog,ety | — | — | 3 | — | **A** | function word (conj) — family-less expected |
| 319 | error | noun | error | 129 | Y | ety | 0/0+3w | 1/1 | 2 | — | **C** | related errar ✓; E4b substring gate ('errar' ⊅ 'error'); Latin etymon 'error<alt:errorem>' also junk-regex-killed so no E3/E4 keys |
| 320 | jamás | adv | never | 128 | Y | cog,der,glossary,inh,inh+,yesno | 0/0+4w | 2/2 | 2 | jamases(noun,0,1), jamás de los jamases(adv,0,1) | **A** | from Occitan ja mais; the related más/ya are component-analysis artifacts, not relatives |
| 321 | Largo | name | a surname | 127 | N | — | — | — | 0 | ~largo(adj,127,16), ~largo(intj,127,16), ~largo(noun,127,16), largometraje(noun,0,1), largoplacista(adj,0,4) | **A** | proper noun — family-less expected |
| 322 | penar | verb | to punish | 127 | N | — | — | — | 2 | Peñaranda(name,0,1), peñarolense(adj,0,1), peñarolense(noun,0,1) | **D** | transparent penar ← pena + -ar; pena exists in DB but the ≥5-char prefix proxy misses it (4-char stem) |
| 323 | secretar | verb | to secrete | 126 | Y | der | — | 1/1 | 0 | secreto(adj,126,9), secreto(noun,126,9), secretario(noun,20,8), secretamente(adv,3,9), secretaría(noun,2,8) | **C** | related secreción ✓; substring gate |
| 324 | novia | noun | a type of sweet roll | 125 | Y | cog,der | 1/0+3w | — | 1 | noviar(verb,125,5), noviazgo(noun,1,5) | **D** | relatives exist in the DB but this entry's own evidence does not connect them |
| 325 | novix | noun | gender-neutral neologism for novio and novia (“r… | 125 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 326 | ambo | noun | suit | 123 | Y | bor+,dercat | — | 1/1 | 0 | — | **A** | borrowed from Italian; related ambos has a different etymon |
| 327 | ay | intj | ah!, alas! | 123 | Y | — | 0/0+4w | — | 1 | — | **A** | function word (intj) — family-less expected |
| 328 | pay | noun | pie (food) | 121 | Y | ety | 0/0+3w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 329 | piar | verb | to chirp, peep, cheep | 121 | Y | m+,onomatopoeic | — | 1/1 | 0 | — | **C** | related pío ✓ (etymology text: 'from pío'); substring gate |
| 330 | negro | noun | a black person; a person of black African descen… | 120 | Y | ety | — | — | 0 | ~negro(adj,120,1), ~negro(noun,120,66), Negros(name,37,1), negroide(noun,0,66), negrofobia(noun,0,1) | **C** | same-word homographs (noun×2, adj) share the identical Latin etymon 'niger<alt:nigrum>' but sit in three families — E5 never merges because the junk regex kills the <alt:>-marked ancestor |
| 331 | negro | adj | black (absorbing all light and reflecting none; … | 120 | Y | ety | 9/9+92w | — | 8 | ~negro(noun,120,1), ~negro(noun,120,66), Negros(name,37,1), negroide(noun,0,66), negrofobia(noun,0,1) | **C** | derived negrillo/negrito/albinegro/carinegro/colinegro/cuellinegro/Montenegro/renegrido/verdinegro ✓ (9 lemmas); entry's Latin etymon 'niger<alt:nigrum>' is junk-regex-killed (<alt: markup) so E4 root-keys and E5 homograph merge both fail; homograph negro-noun sits in a 66-member family |
| 332 | York | name | York | 120 | N | — | 0/0+2w | — | 0 | — | **A** | proper noun — family-less expected |
| 333 | lamentar | verb | to lament, to regret | 120 | Y | cog,der | — | 3/3 | 3 | lamento(noun,120,1), lamentablemente(adv,9,2), lamentable(adj,7,2), lamentación(noun,1,1), Lamentaciones(name,1,1) | **C** | related lamentable/lamentación/lamento ✓ (real deverbals); substring gate |
| 334 | lamento | noun | lament | 120 | Y | der | — | 1/1 | 1 | lamentar(verb,120,1), lamentablemente(adv,9,2), lamentable(adj,7,2), lamentación(noun,1,1), Lamentaciones(name,1,1) | **C** | related lamentar ✓; substring gate |
| 335 | llegado | adj | arrived, received, delivered | 119 | Y | — | — | — | 1 | llegar(verb,250,6), llegada(noun,18,1), llegarle(verb,0,1), llégale(intj,0,1), llegador(noun,0,1) | **C** | prose 'Past participle of llegar' (lemma ✓) |
| 336 | disculpe | intj | excuse me; pardon me | 119 | N | — | — | 2/2 | 2 | disculpar(verb,119,12), disculpa(intj,89,12), disculpa(noun,89,12), discutir(verb,38,6), discurso(noun,36,3) | **A** | function word (intj) — family-less expected |
| 337 | tuyo | pron | yours | 118 | Y | — | — | 19/8 | 0 | — | **A** | function word (pron) — family-less expected |
| 338 | tuyo | det | yours, your | 118 | Y | — | 1/1 | 25/12 | 0 | — | **A** | function word (det) — family-less expected |
| 339 | Campo | name | a surname | 117 | Y | — | — | 1/1 | 0 | ~campo(noun,117,21), Campos(name,20,1), camposanto(noun,0,1), campocorto(noun,0,1), Campoy(name,0,1) | **A** | proper noun — family-less expected |
| 340 | tras | prep | after, following, in the wake of; upon | 117 | Y | etymon,glossary,inh,inh+,yesno | 1/1+3w | — | 1 | — | **A** | function word (prep) — family-less expected |
| 341 | vosotras | pron | you; second person feminine plural personal pron… | 116 | Y | ety | — | 32/26+10w | 1 | vosotres(pron,116,1), vosotros(pron,116,1) | **A** | function word (pron) — family-less expected |
| 342 | vosotres | pron | you (plural) | 116 | N | — | — | 33/27+10w | 0 | vosotras(pron,116,1), vosotros(pron,116,1) | **A** | function word (pron) — family-less expected |
| 343 | vosotros | pron | you, you guys; second person plural personal pro… | 116 | Y | cog,der | — | 32/26+10w | 1 | vosotras(pron,116,1), vosotres(pron,116,1) | **A** | function word (pron) — family-less expected |
| 344 | abogade | noun | lawyer, solicitor, counsel | 116 | N | — | — | — | 0 | abogar(verb,116,1), abogado(noun,116,2), abogacía(noun,1,1), abogador(adj,0,1), abogalla(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 345 | abogar | verb | to advocate | 116 | Y | dbt,ety | — | 5/5 | 0 | abogade(noun,116,1), abogado(noun,116,2), abogacía(noun,1,1), abogador(adj,0,1), abogalla(noun,0,1) | **C** | dbt template names advocar/avocar ✓ + related abogado/abogador ✓ — never loaded; substring gates |
| 346 | terminado | adj | finished | 115 | N | — | — | — | 2 | terminar(verb,115,3), término(noun,17,4), terminal(adj,8,5), terminal(noun,8,5), terminal(noun,8,5) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 347 | mitad | noun | half | 114 | Y | cog,glossary,inh,inh+,yesno | 0/0+3w | 1/1 | 0 | mitad y mitad(adv,0,1) | **C** | related medio ✓ (shared Latin medius); substring gate |
| 348 | viste | intj | you know; used as a space filler, usually in the… | 113 | Y | — | — | — | 2 | — | **A** | function word (intj) — family-less expected |
| 349 | i | noun | The name of the Latin script letter I/i. | 111 | Y | der | 0/0+3w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 350 | ellas | pron | they, them (used subjectively and after preposit… | 111 | Y | glossary,inh,inh+,yesno | 0/0+1w | 33/27+10w | 0 | — | **A** | function word (pron) — family-less expected |
| 351 | tranquilar | verb | to mark with two lines each of the debit and dat… | 110 | Y | ety,surf | — | — | 0 | tranquilo(adj,110,6), tranquilo(intj,110,6), tranquilizar(verb,13,6), tranquilidad(noun,10,2), tranquilamente(adv,6,6) | **C** | surf template 'tranquilo + -ar' names tranquilo (lemma ✓, family of 6); surf template type is not parsed |
| 352 | dama | noun | lady, dame | 109 | Y | bor+,der,doublet,ety | 0/0+6w | — | 4 | — | **C** | doublet template names dueña (lemma ✓) — never loaded |
| 353 | Dan | name | Dan (Biblical character and tribe) | 109 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 354 | dan | noun | dan | 109 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 355 | Sol | name | the Sun | 108 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 356 | sol | noun | sol (a musical note) | 108 | Y | der | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 357 | David | name | David | 107 | Y | der,ety,glossary,inh,inh+,yesno | — | — | 0 | davídico(adj,0,1) | **A** | proper noun — family-less expected |
| 358 | Barco | name | a surname | 103 | N | — | — | — | 0 | ~barco(noun,103,14), barco dragón(noun,0,1), barco pirata(noun,0,1), barco de vapor(noun,0,1), barco pesquero(noun,0,1) | **A** | proper noun — family-less expected |
| 359 | Blanco | name | a surname transferred from the nickname, equival… | 103 | Y | — | — | — | 0 | ~blanco(adj,103,66), ~blanco(noun,103,66), ~blanco(noun,103,66), Blanca(name,59,1), blanca(noun,59,1) | **A** | proper noun — family-less expected |
| 360 | Reunión | name | Réunion (an island, overseas department, and adm… | 102 | N | — | — | — | 0 | ~reunión(noun,102,3), reunir(verb,12,3), reunido(adj,9,1), reunificación(noun,0,6), reunificar(verb,0,6) | **A** | proper noun — family-less expected |
| 361 | ley | noun | law (a well-established characteristic of nature… | 102 | Y | glossary,inh,inh+,yesno | 0/0+45w | 5/5 | 0 | — | **C** | related leal/legal/legislar/legítimo/lindo ✓ (all Latin lex/leg- family lemmas); substring gate blocks all five |
| 362 | Carrera | name | a Spanish surname | 101 | N | — | — | — | 0 | ~carrera(noun,101,3), carrero(noun,101,39), carretera(noun,41,39), carretero(adj,41,39), carretero(noun,41,39) | **A** | proper noun — family-less expected |
| 363 | Hermosa | name | a surname | 100 | Y | — | 0/0+1w | — | 0 | hermoso(adj,100,4), hermosura(noun,2,1), hermosamente(adv,1,4), Hermosillo(name,0,1), hermosear(verb,0,4) | **A** | proper noun — family-less expected |
| 364 | cualquiera | pron | anyone, whoever, whomever | 100 | Y | — | — | — | 1 | ~cualquiera(det,100,1), ~cualquiera(noun,100,1), ~cualquiera(noun,100,1), cualque(adj,0,1) | **A** | function word (pron) — family-less expected |
| 365 | cualquiera | det | any, whatever, whichever | 100 | Y | — | — | — | 0 | ~cualquiera(noun,100,1), ~cualquiera(noun,100,1), ~cualquiera(pron,100,1), cualque(adj,0,1) | **A** | function word (det) — family-less expected |
| 366 | cualquiera | noun | a person of no importance; a nobody, zero | 100 | Y | — | 1/0 | — | 3 | ~cualquiera(det,100,1), ~cualquiera(noun,100,1), ~cualquiera(pron,100,1), cualque(adj,0,1) | **C** | prose 'From cual + quiera' (cual lemma ✓, quiera form of querer ✓); no template |
| 367 | cualquiera | noun | a female prostitute | 100 | Y | — | 1/0 | — | 3 | ~cualquiera(det,100,1), ~cualquiera(noun,100,1), ~cualquiera(pron,100,1), cualque(adj,0,1) | **C** | prose 'From cual + quiera' (cual lemma ✓); no template |

### 1.1 Class counts — the 367

- **A: 258 (70.3%)** — proper nouns, function words, letter names, loans, atomic roots.
- **B: 23 (6.3%)** — Wiktionary has no etymology for the entry.
- **C: 77 (21.0%)** — usable evidence exists; itemised in §1.2.
- **D: 9 (2.5%)** — plausible relatives in the DB, no dictionary evidence.


## 1.2 The C list in full — usable evidence we are failing to use

Grouped by the mechanism that drops the evidence. Each item: **word (pos, freq)** — the evidence and why the edge never forms.

### 1.2.1 `ety`-tree etymons killed by the junk-ancestor regex (`<alt:…>` markup)
- **negro** (adj, freq 120) — derived negrillo/negrito/albinegro/carinegro/colinegro/cuellinegro/Montenegro/renegrido/verdinegro ✓ (9 lemmas); entry's Latin etymon 'niger<alt:nigrum>' is junk-regex-killed (<alt: markup) so E4 root-keys and E5 homograph merge both fail; homograph negro-noun sits in a 66-member family
- **negro** (noun, freq 120) — same-word homographs (noun×2, adj) share the identical Latin etymon 'niger<alt:nigrum>' but sit in three families — E5 never merges because the junk regex kills the <alt:>-marked ancestor

### 1.2.2 `doublet`/`dbt` templates parsed in build.py but NEVER loaded into FamilyBuilder
- **era** (noun, freq 1809) — doublet template names área (lemma ✓) — doublet edges parsed in build.py but never loaded into FamilyBuilder
- **luego** (adv, freq 581) — doublet template names locus (lemma ✓) — never loaded
- **haz** (noun, freq 394) — doublet template names facies/faz (lemmas ✓) — never loaded
- **vetar** (verb, freq 222) — doublet vedar ✓ + related veto ✓ — doublet never loaded; related substring-gated
- **auto** (noun, freq 221) — doublet template names acto (lemma ✓) — never loaded
- **sino** (noun, freq 130) — doublet template names signo (lemma ✓) — never loaded
- **abogar** (verb, freq 116) — dbt template names advocar/avocar ✓ + related abogado/abogador ✓ — never loaded; substring gates
- **dama** (noun, freq 109) — doublet template names dueña (lemma ✓) — never loaded

### 1.2.3 Etymology text names a Spanish parent, but prose is never parsed
- **para** (noun, freq 6691) — prose 'Clipping of paramilitar' (lemma ✓); clipping not parsed
- **xadre** (noun, freq 829) — prose 'padre + gender-neutral x' — names padre (lemma ✓); prose-only
- **amigue** (noun, freq 610) — af template carries only the suffix -e; the base amigo/amiga appears in prose only ('From amigo and amiga…'); bases exist as lemmas (family of 13)
- **dije** (noun, freq 557) — prose 'Derived from dije (I said), an inflection of the verb decir' — names decir (lemma ✓); prose-only
- **hermane** (noun, freq 377) — prose 'From hermano' (lemma ✓); gender-neutral neologism
- **primera** (noun, freq 343) — prose 'From primero' (lemma ✓) — substantivized feminine of primero
- **tíe** (noun, freq 302) — prose 'From tío' (lemma ✓)
- **deja** (noun, freq 284) — prose 'Deverbal from dejar' (lemma ✓)
- **escucha** (noun, freq 253) — prose 'Deverbal from escuchar' (lemma ✓, family of 4)
- **escucha** (noun, freq 253) — prose 'Deverbal from escuchar' (lemma ✓, family of 4)
- **toma** (noun, freq 243) — prose 'Deverbal from tomar' (lemma ✓)
- **listar** (verb, freq 224) — prose 'From lista' (lemma ✓)
- **pregunta** (noun, freq 212) — prose 'Deverbal from preguntar' (lemma ✓, family of 4)
- **trata** (noun, freq 198) — prose 'Deverbal from tratar' (lemma ✓, family of 6)
- **tampoco** (adv, freq 197) — etymology tree lists Spanish tan and Spanish poco (both lemmas ✓) and prose 'Univerbation of tan + poco'; Spanish tree-ancestors are parsed but never used to link
- **recuerdo** (noun, freq 176) — prose 'Deverbal from recordar' (lemma ✓)
- **querida** (noun, freq 148) — prose 'From querer' (lemma ✓)
- **querido** (adj, freq 148) — prose 'Past participle of querer' (lemma ✓)
- **querido** (noun, freq 148) — prose 'Past participle of querer' (lemma ✓)
- **acabo** (noun, freq 134) — prose 'Deverbal from acabar' (lemma ✓) despite synonym-redirect gloss
- **llegado** (adj, freq 119) — prose 'Past participle of llegar' (lemma ✓)
- **cualquiera** (noun, freq 100) — prose 'From cual + quiera' (cual lemma ✓, quiera form of querer ✓); no template
- **cualquiera** (noun, freq 100) — prose 'From cual + quiera' (cual lemma ✓); no template

### 1.2.4 Prose parent AND related list, both unused
- **trato** (noun, freq 140) — ety template 'Deverbal from tratar' (lemma ✓, family of 6) + related trata/tratable/tratadista/tratado/tratamiento/tratar ✓; deverbal-prose not parsed; substring gates

### 1.2.5 Template types wiktextract emits that the parser has no case for (`surf`, `prothetic form`, `back-form`, `abbrev`)
- **A** (noun, freq 22560) — abbrev template 'Abbreviation of alfil' names alfil (lemma ✓); abbrev template type is not parsed
- **amo** (noun, freq 196) — back-form template 'Back-formation from ama' names ama (lemma ✓); back-form template type is not parsed
- **tranquilar** (verb, freq 110) — surf template 'tranquilo + -ar' names tranquilo (lemma ✓, family of 6); surf template type is not parsed
- **dentrar** (verb, freq 316) — 'prothetic form' template names entrar (lemma ✓) + 'surf' template 'dentro + -ar' names dentro (lemma ✓); neither template type is parsed

### 1.2.6 `deverbal` template yields an empty affix — E1 skips it
- **prueba** (noun, freq 153) — deverbal template → base probar (lemma ✓) with EMPTY affix — E1 skips empty-affix edges; related probar also listed

### 1.2.7 Derivational suffix `-e` sits in E1's inflectional-desinence reject list
- **niñe** (noun, freq 304) — af template niña + -e; base niña lemma ✓; suffix -e is in E1's inflectional-desinence reject list (…,a,e,o,…)

### 1.2.8 Derived list + prose parent; multiple E4 gates
- **mira** (noun, freq 826) — derived mirilla ✓ — substring passes; blocked by rid<=lid ordering + allomorph + root-keys (deverbal-prose entry has no Latin etymons); prose 'Deverbal from mirar' (lemma ✓)

### 1.2.9 RAW-case substring/word-group keys split accent variants (`aún`/`aun`, `gombo`/`gombó`, `dónde`/`donde`)
- **aún** (adv, freq 508) — related aun ✓ — accent-variant pair of one lexeme; RAW-case substring gate ('aun' ⊄ 'aún') and no-forms source keep them apart
- **dónde** (adv, freq 1275) — related adónde/donde ✓; substring gate is RAW-case ('dónde' ⊅ 'donde'); source adv has no forms

### 1.2.10 Adverbs carry no form records in Wiktionary — ineligible as E4/E4b sources
- **así** (adv, freq 2481) — derived asá/asimismo ✓; source adv has no forms
- **fuera** (adv, freq 736) — related afuera ✓ ('afuera' contains 'fuera', substring passes); source adv has no forms → E4b skipped
- **dentro** (adv, freq 316) — derived adentro ✓; source adv has no forms → E4/E4b skipped
- **arriba** (adv, freq 242) — related riba/ribera/ribero ✓ ('arriba' contains 'riba', substring passes); source adv has no forms
- **encima** (adv, freq 133) — derived encimera ✓; E4 source eligibility requires form records — adverbs without forms are skipped
- **acerca** (adv, freq 175) — related acercar ✓ ('acercar' contains 'acerca', substring passes) + cerca ✓; source adv has no forms
- **anoche** (adv, freq 163) — derived anteanoche ✓ + related noche ✓; source adv has no forms

### 1.2.11 Invariable words carry no form records — ineligible as sources/parents
- **gracias** (noun, freq 1842) — related gracia ✓ ('gracias' contains 'gracia', substring passes) + agradecer ✓; source ineligible: gracias noun has NO form records

### 1.2.12 The parent is a proper noun — ineligible as an E1 parent
- **adiós** (noun, freq 339) — compound template a + Dios; base Dios is a name-pos lemma (ineligible as E1 parent)

### 1.2.13 The parent is in _FUNC_STOPLIST — ineligible as an E1 parent
- **demás** (adj, freq 139) — af template de- + más; base más is in _FUNC_STOPLIST (ineligible E1 parent); derived además/demasiado ✓ also listed
- **demás** (adv, freq 139) — af template de- + más; base más in _FUNC_STOPLIST

### 1.2.14 The parent is an adverb without forms — ineligible as an E1 parent
- **además** (adv, freq 178) — univerbation template a + demás; base demás adj has no form records (ineligible E1 parent)
- **afuera** (adv, freq 150) — af template a- + fuera; base fuera adv carries no forms (ineligible E1 parent); derived afuerino/afuerita ✓ + related afueras ✓
- **encimar** (verb, freq 133) — suffix template encima + -ar; base encima adv carries no forms (ineligible E1 parent)

### 1.2.15 `related` list blocked by the deliberate E4b substring gate
- **ano** (noun, freq 965) — related anal ✓ (ano + -al, real suffixation); substring gate ('anal' ⊅ 'ano')
- **hija** (noun, freq 633) — related hijo ✓ (gender pair of one lexeme); substring gate ('hija' ⊅ 'hijo')
- **necesitar** (verb, freq 561) — related necesario/necesidad/necesitado ✓; substring gate
- **manar** (verb, freq 266) — related emanar/manantial ✓; substring gate
- **puntar** (verb, freq 253) — related apuntar/punto/puntuar ✓ (etymology text: 'From punto'); substring gate
- **mediar** (verb, freq 190) — related mediación/mediador/medio ✓; substring gate
- **detrás** (adv, freq 148) — related atrás ✓ (morphological sibling, de+tras / a+tras); substring gate ('atrás' ⊅ 'detrás')
- **suceder** (verb, freq 131) — related suceso ✓; substring gate
- **siguiente** (adj, freq 131) — related seguir/seguidor ✓ (old present participle of seguir); substring gate
- **secretar** (verb, freq 126) — related secreción ✓; substring gate
- **piar** (verb, freq 121) — related pío ✓ (etymology text: 'from pío'); substring gate
- **lamentar** (verb, freq 120) — related lamentable/lamentación/lamento ✓ (real deverbals); substring gate
- **lamento** (noun, freq 120) — related lamentar ✓; substring gate
- **mitad** (noun, freq 114) — related medio ✓ (shared Latin medius); substring gate
- **ley** (noun, freq 102) — related leal/legal/legislar/legítimo/lindo ✓ (all Latin lex/leg- family lemmas); substring gate blocks all five

### 1.2.16 Related list (substring gate) AND junk-regex-killed etymon
- **error** (noun, freq 129) — related errar ✓; E4b substring gate ('errar' ⊅ 'error'); Latin etymon 'error<alt:errorem>' also junk-regex-killed so no E3/E4 keys

### 1.2.17 Related list blocked by substring + allomorph gates
- **restar** (verb, freq 146) — related restante/resto ✓ (real deverbals); substring + allomorph gates

### 1.2.18 Related list: substring gate + adverb source without forms
- **después** (adv, freq 736) — related pues ✓ (shared Latin post); substring gate + adv has no forms

### 1.2.19 `derived` list blocked by the deliberate E4 gates (shared Latin root keys / allomorphs)
- **haya** (noun, freq 252) — derived hayedo ✓ (haya + -edo); E4 root-key gate (target has no Latin etyma)
- **bebé** (noun, freq 209) — derived portabebés ✓ (compound); E4 root-key gate — French etymon, no Latin roots on source

**Counts by mechanism (hi band, n=77):**

- `ety`-tree etymons killed by the junk-ancestor regex (`<alt:…>` markup): **2**
- `doublet`/`dbt` templates parsed in build.py but NEVER loaded into FamilyBuilder: **8**
- Etymology text names a Spanish parent, but prose is never parsed: **23**
- Prose parent AND related list, both unused: **1**
- Template types wiktextract emits that the parser has no case for (`surf`, `prothetic form`, `back-form`, `abbrev`): **4**
- `deverbal` template yields an empty affix — E1 skips it: **1**
- Derivational suffix `-e` sits in E1's inflectional-desinence reject list: **1**
- Derived list + prose parent; multiple E4 gates: **1**
- RAW-case substring/word-group keys split accent variants (`aún`/`aun`, `gombo`/`gombó`, `dónde`/`donde`): **2**
- Adverbs carry no form records in Wiktionary — ineligible as E4/E4b sources: **7**
- Invariable words carry no form records — ineligible as sources/parents: **1**
- The parent is a proper noun — ineligible as an E1 parent: **1**
- The parent is in _FUNC_STOPLIST — ineligible as an E1 parent: **2**
- The parent is an adverb without forms — ineligible as an E1 parent: **3**
- `related` list blocked by the deliberate E4b substring gate: **15**
- Related list (substring gate) AND junk-regex-killed etymon: **1**
- Related list blocked by substring + allomorph gates: **1**
- Related list: substring gate + adverb source without forms: **1**
- `derived` list blocked by the deliberate E4 gates (shared Latin root keys / allomorphs): **2**
Of these 77, **40 are plain extraction bugs** (junk-regex, doublet-unloaded, prose parents, unparsed
template types, empty-affix, `-e` reject, raw-string keys — categories 1.2.1–1.2.9): the evidence is
already in the dump in machine-readable form and no precision guard argues against using it. The other
**37 need a deliberate gate/eligibility decision to be revisited** (categories 1.2.10–1.2.19).


## 2. Stratified sample (60 per band, seed 42)

Same columns as §1.


### Band `10<=f<100`

| # | word | pos | gloss | freq | etym | tpl | der | rel | syn | mates (≤5) | cls | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Sala | name | a surname | 99.51 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 2 | principio | noun | principle | 92.50 | Y | ety | 0/0+15w | 2/2 | 5 | principiar(verb,93,3), principal(adj,66,6), principal(noun,66,6), príncipe(adj,51,5), príncipe(noun,51,5) | **C** | related principiante/principiar ✓; substring gate |
| 3 | delante | adv | in front of, before (spatially) | 91.89 | Y | af,etymon,glossary,inh,inh+,yesno | 2/2+6w | 1/1 | 0 | ~delante(prep,92,1), delantera(noun,8,1), delantero(adj,8,3), delantero(noun,8,3), delantal(noun,4,1) | **C** | derived adelante/delantal ✓ + related antes ✓; source adv has no forms |
| 4 | izquierda | noun | left (side, direction) | 81.81 | Y | bor+,cog | 1/1+2w | — | 0 | izquierdo(adj,82,1), Izquierdo(name,19,1), izquierdista(adj,0,5), izquierdista(noun,0,5), izquierdazo(noun,0,1) | **C** | derived izquierdista ✓; source ineligible: no form records; Basque etymon → no Latin roots for E4 |
| 5 | apenas | adv | barely, scarcely | 80.25 | Y | glossary,inh,inh+,yesno | — | 0/0+1w | 8 | apenar(verb,80,6), apenado(adj,3,1), apenas si(adv,0,1) | **D** | relatives exist in the DB but this entry's own evidence does not connect them |
| 6 | té | noun | tea | 75.71 | Y | bor,cog,dbt | 1/0+19w | 1/1 | 1 | — | **C** | doublet cha ✓ — never loaded |
| 7 | llavir | verb | to lock | 75.36 | N | — | — | — | 0 | llavín(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 8 | Bob | name | a male given name from English | 66.27 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 9 | entrado | adj | after the start of; into; (late) into; (well) in… | 63.33 | N | — | — | — | 1 | entrar(verb,428,4), entrada(noun,63,4), entraña(noun,5,2), entrañar(verb,5,2), entrabar(verb,5,3) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 10 | enemigue | noun | enemy | 61.71 | Y | -a-o-e,-a-o-x,glossary | — | — | 0 | enemigo(adj,62,5), enemigo(noun,62,5), enemistad(noun,1,1), enemistar(verb,1,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 11 | vuestro | det | yours, your, to you | 58.37 | Y | glossary,inh,inh+,yesno | 0/0+4w | 25/12 | 0 | ~vuestro(pron,58,1), vuestra merced(pron,0,1), vuestra señoría(pron,0,1), vuestra excelencia(pron,0,1), vuestra reverencia(pron,0,1) | **A** | function word (det) — family-less expected |
| 12 | ex | adj | former, ex- (referring to a condition that has e… | 46.72 | Y | — | — | — | 0 | — | **A** | self-reference ('From ex'); no parent lemma |
| 13 | Daniel | name | Daniel (biblical book and prophet) | 46.05 | N | — | 1/1 | 1/1 | 0 | Daniela(name,1,1), Daniense(name,0,1), danielista(noun,0,1) | **A** | proper noun — family-less expected |
| 14 | Kevin | name | a male given name from English, equivalent to En… | 44.01 | Y | ety | — | — | 0 | — | **A** | proper noun — family-less expected |
| 15 | Larry | name | a male given name from English | 37.91 | Y | ety | — | — | 0 | — | **A** | proper noun — family-less expected |
| 16 | roso | adj | hairless | 37.08 | Y | ety | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 17 | indio | noun | a native of India | 35.16 | Y | ety | 0/0+5w | — | 0 | ~indio(adj,35,1), ~indio(noun,16,1), indio viejo(noun,0,1), indio desnudo(noun,0,1) | **C** | prose 'From India' (lemma ✓, name) |
| 18 | construir | verb | to build | 34.66 | Y | ety | — | 3/3 | 0 | construcción(noun,19,2), constantemente(adv,14,4), constante(adj,13,4), constante(noun,13,4), construido(adj,12,1) | **C** | related construcción/constructivo/constructor ✓; substring gate |
| 19 | Clara | name | a female given name, equivalent to English Clara | 34.65 | N | — | 1/0 | 1/1 | 0 | claramente(adv,39,11), ~clara(noun,35,1), claraboya(noun,0,1), clarado(adj,0,11) | **A** | proper noun — family-less expected |
| 20 | Castillo | name | a habitational surname | 32.33 | Y | — | — | — | 0 | ~castillo(noun,32,3), castigo(noun,26,1), castigar(verb,26,5), castigado(adj,9,5), casting(noun,2,1) | **A** | proper noun — family-less expected |
| 21 | limpia | noun | cleansing, cleaning | 31.99 | Y | ety | — | — | 0 | limpio(adj,43,8), limpiar(verb,43,8), limpieza(noun,20,8), limpiador(adj,3,8), limpiador(noun,3,8) | **C** | prose 'Deverbal from limpiar' (lemma ✓, family of 8) |
| 22 | lord | noun | lord (British title) | 30.06 | Y | bor+,der | — | 1/1 | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 23 | usado | adj | used | 29.87 | N | — | — | — | 0 | usador(noun,0,7) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 24 | armario | noun | storage cabinet, wardrobe, cupboard | 29.45 | Y | doublet,ety | 0/0+4w | — | 5 | armar(verb,187,8), armarla(verb,0,1), armar un lío(verb,0,1), armarse un lío(verb,0,1), armarse la gorda(verb,0,1) | **C** | doublet armero ✓ — never loaded |
| 25 | doce | num | twelve | 26.66 | Y | cog,ety,glossary,inh,inh+,yesno | — | 5/5 | 0 | — | **A** | function word (num) — family-less expected |
| 26 | súper | adj | superb, great | 25.85 | Y | — | 0/0+1w | — | 0 | superior(adj,37,5), superior(noun,37,5), superficie(noun,24,4), ~super(adj,19,1), superar(verb,17,3) | **C** | prose 'From super' (lemma ✓) — accent-variant homograph; RAW-string word-group keys keep them apart |
| 27 | mato | noun | bushes | 25.61 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 28 | Pasión | name | a male given name | 25.02 | Y | der,glossary,inh,inh+,yesno | — | — | 0 | ~Pasión(name,25,1), ~pasión(noun,25,5), pasional(adj,2,1), pasionaria(noun,0,5), pasionario(adj,0,1) | **A** | proper noun — family-less expected |
| 29 | aprecio | noun | appreciation | 23.91 | Y | ety | — | — | 1 | apreciar(verb,24,8), apreciación(noun,1,1), apreciable(adj,0,8), apreciador(adj,0,8), apreciador(noun,0,8) | **C** | prose 'Deverbal from apreciar' (lemma ✓) |
| 30 | tripulación | noun | crew of a ship, plane, or other craft | 23.16 | Y | cog,der | — | 2/2 | 0 | tripulante(noun,2,1), tripular(verb,1,1), tripulado(adj,1,1), tripudo(adj,0,9), tripunto(noun,0,38) | **C** | related tripulante/tripular ✓; substring gate |
| 31 | salvado | noun | bran | 22.30 | Y | — | — | — | 1 | salvar(verb,108,5), salvaje(adj,30,7), salvaje(noun,30,7), salva(noun,12,5), Salvador(name,10,1) | **D** | relatives exist in the DB but this entry's own evidence does not connect them |
| 32 | empleado | noun | employee | 22.07 | Y | — | 0/0+1w | 1/1 | 0 | empleo(noun,33,7), emplear(verb,33,6), ~empleado(adj,22,4), empleada(noun,6,1), empleador(adj,2,6) | **C** | related empleador ✓ — substring passes; allomorph gate blocks because strip_one_prefix('empleador')='pleador' (fossilized em- stripped as if a Spanish prefix); prose 'Past participle of emplear' (lemma ✓) |
| 33 | León | name | a male given name, equivalent to English Leon | 19.90 | Y | der | — | — | 0 | — | **A** | proper noun — family-less expected |
| 34 | risa | noun | laugh, laughter (sound of laughing) | 18.54 | Y | glossary,inh,inh+,yesno | 1/0+20w | 2/2 | 0 | — | **C** | related reír ✓ + sonrisa ✓ ('sonrisa' contains 'risa', substring passes); E4b allomorph gate blocks sonrisa (does not START with risa) |
| 35 | Alegre | name | a surname | 18.40 | Y | — | — | — | 0 | alegrar(verb,88,6), Alegría(name,33,1), alegría(noun,33,1), ~alegre(adj,18,6), alegremente(adv,2,6) | **A** | proper noun — family-less expected |
| 36 | vendido | noun | sellout | 18.19 | N | — | — | — | 0 | vendimia(noun,0,3), vendimiar(verb,0,3), vendible(adj,0,7), vendita(noun,0,4), vendimiario(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 37 | continuación | noun | continuation | 17.53 | Y | ety,surf | 0/0+1w | 1/1 | 0 | contigo(adv,478,1), continuar(verb,40,5), continuo(adj,12,6), continente(noun,7,7), continuamente(adv,6,6) | **C** | related continuar ✓ + 'surf' template continuar + -ción (unparsed); substring gate |
| 38 | colina | noun | choline | 17.14 | Y | bor+ | — | — | 0 | ~colina(noun,17,2), colín(noun,0,19), colindante(adj,0,6), colinesterasa(noun,0,1), colinabo(noun,0,1) | **A** | biochemical loanword; homograph of colina 'hill' correctly split; mate colín is a false friend |
| 39 | auxilio | noun | aid, help | 16.33 | Y | ety | 0/0+2w | 1/1 | 1 | auxiliar(verb,16,1), auxiliar(adj,4,2), auxiliar(noun,4,2), auxiliador(adj,0,2), auxiliador(noun,0,2) | **C** | related auxiliar ✓; substring gate |
| 40 | confundir | verb | to confuse, to throw off, to baffle, to perplex | 16.16 | Y | doublet,ety | — | 2/2 | 1 | confundido(adj,16,1), confusión(noun,12,1), confuso(adj,11,2), Confucio(name,1,1), confusamente(adv,0,2) | **C** | doublet cohonder ✓ + related confusión ✓ |
| 41 | Duque | name | a surname | 15.07 | N | — | — | — | 0 | ~duque(noun,15,5), duquesa(noun,15,5) | **A** | proper noun — family-less expected |
| 42 | güey | noun | chump, punk, dumbass, idiot, jerk | 14.99 | Y | dercat,m+ | — | 1/1 | 36 | — | **C** | etymology text names Spanish parent buey (pronunciation variant, lemma ✓); prose-only, no template |
| 43 | Pablo | name | Paul (biblical character) | 14.82 | Y | der,glossary,inh,inh+,yesno | — | — | 0 | ~Pablo(name,15,1) | **A** | proper noun — family-less expected |
| 44 | Marte | name | Mars (Roman god of war) | 14.64 | Y | ety | 1/1 | 1/1 | 0 | martes(noun,26,1), Martel(name,1,1), Martell(name,0,1), martensítico(adj,0,1), marteño(adj,0,1) | **A** | proper noun — family-less expected |
| 45 | Vietnam | name | Vietnam (a country in Southeast Asia) | 13.85 | Y | der | — | 1/1 | 0 | vietnamita(adj,2,1), vietnamita(noun,2,1), vietnamita(noun,2,1), vietnamización(noun,0,1) | **A** | proper noun — family-less expected |
| 46 | Franco | name | a male given name, equivalent to English Frank | 13.46 | N | — | 2/2 | — | 0 | Francia(name,47,1), francés(adj,38,15), francés(noun,38,15), francés(noun,38,15), francés(noun,38,15) | **A** | proper noun — family-less expected |
| 47 | Miró | name | a surname from Catalan | 13.01 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 48 | Dolores | name | a female given name from Old Spanish [in turn fr… | 13.01 | Y | — | — | — | 0 | dolor(noun,121,6), doloroso(adj,13,6), dolorido(adj,1,6), dolorosamente(adv,1,6), doloridamente(adv,0,6) | **A** | proper noun — family-less expected |
| 49 | ranchar | verb | to hang out in someone's house | 12.89 | N | — | — | — | 2 | rancho(noun,13,6), ranchero(adj,1,6), ranchero(noun,1,6), ranchera(noun,0,1), ranchería(noun,0,6) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 50 | construido | adj | constructed | 12.44 | N | — | — | — | 0 | construir(verb,35,1), construcción(noun,19,2), constantemente(adv,14,4), constante(adj,13,4), constante(noun,13,4) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 51 | Carla | name | a female given name, masculine equivalent Carlos | 12.19 | N | — | — | — | 0 | carlanca(noun,0,1) | **A** | proper noun — family-less expected |
| 52 | hadar | verb | to determine by fate | 12.05 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 53 | impresionado | adj | impressed | 11.89 | N | — | — | — | 0 | impresionante(adj,41,10), impresión(noun,28,10), impresionar(verb,12,10), imprenta(noun,3,1), impredecible(adj,3,24) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 54 | dificultad | noun | difficulty, trouble, problem, challenge, constra… | 11.76 | Y | bor+,cog | 0/0+2w | 1/1 | 0 | difícil(adj,248,2), dificultar(verb,7,5), difícilmente(adv,5,2), dificultoso(adj,0,5), dificultosamente(adv,0,5) | **C** | related difícil ✓; substring gate |
| 55 | privacidad | noun | privacy | 11.63 | N | — | — | — | 1 | privar(verb,44,4), privado(adj,44,4), privada(noun,26,1), privación(noun,1,1), priva(noun,1,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 56 | aliade | noun | ally | 10.71 | Y | -a-o-e,-a-o-x,glossary | — | — | 0 | aliado(adj,11,2), aliado(noun,11,1), ~aliade(noun,0,1), aliadófilo(adj,0,2), aliadófilo(noun,0,1) | **D** | same-word entry in another family; no usable link evidence here |
| 57 | criado | noun | servant | 10.48 | Y | — | — | — | 2 | criada(noun,10,3), ~Criado(name,10,1), criadero(noun,1,7), criador(noun,1,7), criadilla(noun,0,3) | **C** | prose 'Past participle of criar' (lemma ✓) |
| 58 | acceder | verb | to accede, to agree, to concur | 10.38 | Y | ety | — | 4/4 | 2 | accedente(adj,0,1) | **C** | related acceso/accesible/accesión/accesar ✓; substring gate; Latin etymon junk-regex-killed |
| 59 | Irene | name | a female given name from Ancient Greek | 10.16 | Y | ety | — | — | 0 | Irenea(name,0,1), Ireneo(name,0,1) | **A** | proper noun — family-less expected |
| 60 | Polo | name | a surname | 10.01 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |

### Band `1<=f<10`

| # | word | pos | gloss | freq | etym | tpl | der | rel | syn | mates (≤5) | cls | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | sip | intj | yep, yeah, uh-huh | 9.80 | Y | cal | — | — | 0 | — | **A** | function word (intj) — family-less expected |
| 2 | Hugo | name | a male given name, equivalent to English Hugh or… | 9.05 | Y | der | 0/0+1w | — | 0 | — | **A** | proper noun — family-less expected |
| 3 | Amarilla | name | a surname | 8.24 | N | — | — | — | 0 | Amarillo(name,16,1), amarillo(adj,16,18), amarillo(noun,16,18), amarillento(adj,0,18), amarizar(verb,0,1) | **A** | proper noun — family-less expected |
| 4 | Héctor | name | Hector | 7.90 | Y | ety | — | — | 0 | hectolitro(noun,0,8), hectogramo(noun,0,13), hectopascal(noun,0,2), hectómetro(noun,0,1), hecto-(prefix,0,1) | **A** | proper noun — family-less expected |
| 5 | Monje | name | a surname originating as an occupation | 7.27 | Y | doublet | — | — | 0 | ~monje(noun,7,4), monjería(noun,0,4) | **A** | proper noun — family-less expected |
| 6 | cristino | noun | a supporter of Isabella II of Spain during the C… | 6.84 | Y | — | — | — | 1 | Cristo(name,26,1), cristo(noun,26,2), cristal(noun,24,16), cristiane(noun,10,1), cristiano(adj,10,9) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 7 | motocicleta | noun | motorcycle | 6.31 | Y | bor+,surf | — | 1/1 | 1 | motociclista(noun,1,3), motocross(noun,0,1), motociclismo(noun,0,1), motocarro(noun,0,39), motocrós(noun,0,1) | **C** | related motociclismo ✓; 'surf' (surface-analysis) template moto- + bicicleta is not parsed; substring gate |
| 8 | Félix | name | a male given name, equivalent to English Felix | 6.24 | Y | ety | — | — | 0 | — | **A** | proper noun — family-less expected |
| 9 | investigado | adj | investigated | 6.00 | N | — | — | — | 0 | investigación(noun,93,26), investigar(verb,21,26), investigador(adj,9,4), investigador(noun,9,4), investidura(noun,0,26) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 10 | cierro | noun | close, closing | 5.87 | Y | ety | — | — | 0 | cierre(noun,22,43), cierrabares(noun,0,1), cierre patronal(noun,0,1), cierra la puerta al s…(intj,0,1) | **C** | prose 'Deverbal from cerrar' (lemma ✓) |
| 11 | Delhi | name | Delhi (a megacity and union territory of India, … | 5.56 | N | — | 1/1+1w | — | 0 | delhita(adj,0,1), delhita(noun,0,1) | **A** | proper noun — family-less expected |
| 12 | cerear | verb | to rummage through something without permission … | 5.16 | N | — | — | — | 0 | cereal(noun,5,5), cerealero(adj,0,5), cerealista(adj,0,5), cerealista(noun,0,5), cerealístico(adj,0,5) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 13 | cesar | verb | to cease (to stop) | 5.08 | Y | bor+,doublet | 4/4+1w | 1/1 | 7 | ~César(name,15,1), ~césar(noun,15,1), ~Cesar(name,5,1), cesárea(noun,2,1), cesáreo(adj,2,1) | **C** | doublet cejar ✓ + derived cesamiento/cesante/cesantía/cese ✓ |
| 14 | Armando | name | a male given name from French Armand, equivalent… | 4.34 | N | — | — | — | 0 | Armañac(name,0,1), armañac(noun,0,1) | **A** | proper noun — family-less expected |
| 15 | choco | adj | blind. | 4.17 | N | — | 0/0+1w | — | 1 | chocolate(noun,37,9), ~Chocó(name,4,1), ~choco(adj,4,1), ~Choco(name,1,1), ~Choco(name,1,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 16 | Connecticut | name | Connecticut (a state in the northeastern United … | 4.12 | Y | bor+,der | — | — | 0 | — | **A** | proper noun — family-less expected |
| 17 | jaquir | verb | to forsake, to abandon | 4.08 | Y | ety | — | — | 2 | jáquima(noun,0,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 18 | Atenas | name | Athens (the capital city of Greece) | 3.76 | N | — | — | 1/1 | 0 | atenazar(verb,0,5), atenacear(verb,0,1) | **A** | proper noun — family-less expected |
| 19 | bronceado | noun | a tan, a suntan | 3.74 | N | — | — | — | 0 | bronce(noun,4,4), broncear(verb,4,4), ~bronceado(adj,4,1), bronca(noun,3,2), bronco(adj,3,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 20 | bourbon | noun | bourbon | 3.64 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 21 | anti | adj | anti-, opposing | 3.42 | Y | — | — | — | 0 | — | **A** | self-reference ('From anti'); no parent lemma |
| 22 | nómina | noun | payroll | 3.27 | Y | cog,der,glossary,inh,inh+,yesno | — | 1/1+1w | 4 | nominar(verb,2,2), nominado(adj,2,1), nominado(noun,2,1), nominación(noun,2,1), nominal(adj,1,8) | **C** | related nombre ✓ (Latin nomen family); substring gate |
| 23 | depredador | noun | predator | 3.12 | N | — | — | 1/1 | 1 | depresión(noun,10,2), ~depredador(adj,3,2), depresivo(adj,1,3), depre(adj,0,1), depre(noun,0,1) | **C** | related depredar ✓ (depredar + -dor); substring gate |
| 24 | rienda | noun | rein(s) (strap or rope attached to a bridle or b… | 3.10 | Y | cog,der,glossary,inh,inh+,noncog,yesno | 0/0+8w | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 25 | retardado | noun | retard | 2.99 | N | — | — | — | 0 | retar(verb,17,4), retardar(verb,3,3), ~retardado(adj,3,1), retardo(noun,0,1), retardante(noun,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 26 | protectora | noun | animal shelter (an organization that provides te… | 2.87 | N | — | — | — | 1 | proteger(verb,46,25), protección(noun,38,7), protegido(adj,10,2), protector(adj,9,4), protector(noun,9,4) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 27 | perturbado | adj | disturbed, upset, agitated | 2.85 | N | — | — | — | 0 | perturbar(verb,3,5), perturbador(adj,2,5), perturbador(noun,2,5), perturbación(noun,1,5), perturbante(adj,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 28 | seta | noun | mushroom | 2.65 | Y | der,unc | 0/0+1w | — | 3 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 29 | Tamara | name | a female given name, equivalent to English Tamar… | 2.55 | N | — | — | — | 0 | tamarindo(noun,0,1), tamarisco(noun,0,1), tamariz(noun,0,1), tamarino(noun,0,1), tamare(intj,0,1) | **A** | proper noun — family-less expected |
| 30 | prodigio | noun | prodigy (an especially gifted or talented person… | 2.51 | Y | der | 1/1+1w | — | 1 | pródigo(adj,1,2), prodigioso(adj,0,2), prodigar(verb,0,1), prodigiosamente(adv,0,2), pródigamente(adv,0,2) | **C** | derived prodigioso ✓; E4 gates |
| 31 | suroeste | noun | southwest | 2.34 | N | — | — | — | 1 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 32 | ancha | noun | large town | 2.30 | N | — | — | — | 0 | anchar(verb,6,1), anchamente(adv,0,7) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 33 | referente | noun | referent | 2.28 | Y | — | — | — | 0 | referir(verb,61,31), referencia(noun,10,5), referenciar(verb,10,5), ~referente(adj,2,2), referéndum(noun,1,1) | **C** | prose 'From referir' (lemma ✓) |
| 34 | purgatorio | noun | purgatory | 2.26 | Y | lbor | — | — | 0 | ~purgatorio(adj,2,1), purga(noun,1,1), purgar(verb,1,4), purgante(adj,0,2), purgante(noun,0,2) | **D** | relatives exist in the DB but this entry's own evidence does not connect them |
| 35 | licenciado | noun | bachelor (person having the first university deg… | 2.19 | N | — | — | — | 0 | licencia(noun,29,4), licenciar(verb,29,4), ~licenciado(adj,2,1), licenciatura(noun,1,1), licenciamiento(noun,0,4) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 36 | santificado | adj | sanctified, hallowed, made holy | 2.08 | N | — | — | — | 0 | santidad(noun,6,1), Santiago(name,5,1), santificar(verb,2,2), santiamén(noun,2,1), Santi(name,1,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 37 | Almendras | name | a toponymic surname | 2.06 | Y | — | — | — | 0 | almendra(noun,2,5), almendrar(verb,2,5), Almendra(name,1,1), almena(noun,0,4), almenar(verb,0,4) | **A** | proper noun — family-less expected |
| 38 | voladora | noun | a small bus used for public transportation | 2.05 | N | — | — | — | 0 | volado(adj,6,4), volado(noun,6,1), volador(adj,4,2), volador(noun,4,1), volada(noun,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 39 | surfear | verb | to surf | 2.01 | Y | af,bor+ | — | — | 0 | surfero(adj,0,1), surfero(noun,0,1), surfeador(noun,0,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 40 | corán | noun | Qur'an | 1.96 | N | — | — | — | 0 | ~Corán(name,2,1), coránico(adj,0,1), coranista(noun,0,1) | **A** | lowercase variant of the proper noun Corán |
| 41 | pediatra | noun | pediatrician | 1.89 | N | — | — | 2/2 | 0 | pediatría(noun,2,1), pediátrico(adj,1,1) | **C** | related pediatría/pediátrico ✓; substring gate |
| 42 | adoptivo | adj | foster, adoptive (providing parental care to unr… | 1.80 | Y | ety | — | 2/2 | 0 | adoptar(verb,6,2), adoptado(adj,4,1), adoptado(noun,4,1), adoptando(noun,1,1), adoptante(adj,0,1) | **C** | related adopción/adoptar ✓; substring gate |
| 43 | mástil | noun | mast (a tall, slim post or tower used to support… | 1.72 | Y | der | — | 1/1 | 3 | masticar(verb,3,4), masticable(adj,0,4), mastín(noun,0,1), masticación(noun,0,1), mastitis(noun,0,1) | **C** | related mastelero ✓ (mástel + -ero); substring gate |
| 44 | hámster | noun | hamster | 1.68 | Y | bor,bor+,cog,der | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 45 | hostal | noun | hostel; cheap hotel | 1.50 | Y | bor,der,doublet,glossary,inh,inh+,yesno | — | 2/2 | 1 | hostaje(noun,0,1) | **C** | doublet hospital ✓ + related hospital/huésped ✓ |
| 46 | pool | noun | pool (sport) | 1.43 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 47 | celebrado | adj | celebrated | 1.37 | N | — | — | — | 1 | celebrar(verb,25,2), celebración(noun,11,1), celebridad(noun,5,1), célebre(adj,2,2), celebrity(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 48 | coliseo | noun | coliseum | 1.35 | N | — | — | — | 0 | colisión(noun,3,3), ~Coliseo(name,1,1), colisionar(verb,1,3), colisionador(noun,0,1), colista(noun,0,19) | **D** | same-word entry exists in another family; no etymological evidence here |
| 49 | restaurado | adj | restored | 1.34 | N | — | — | — | 0 | restar(verb,146,1), restaurante(noun,55,2), restaurar(verb,4,1), restante(adj,3,1), restante(noun,3,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 50 | aye | noun | whine; whining; whinging | 1.32 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 51 | proveniente | adj | coming (from), originating (from) | 1.32 | Y | — | — | 3/1 | 1 | provecho(intj,7,12), provecho(noun,7,12), provenir(verb,7,56), proveedor(noun,5,3), proveer(verb,2,3) | **C** | related proveniencia ✓ + prose 'From provenir' (lemma ✓, family of 56) |
| 52 | yonqui | noun | junkie, drug addict | 1.30 | Y | ety | — | — | 1 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 53 | tranqui | adj | relaxed; chilled | 1.22 | Y | ety | — | — | 0 | tranquilo(adj,110,6), tranquilo(intj,110,6), tranquilar(verb,110,1), tranquilizar(verb,13,6), tranquilidad(noun,10,2) | **C** | ety template 'Clipping of tranquilo' (lemma ✓, family of 6); clipping link not extracted |
| 54 | comporte | noun | comport, behavior | 1.19 | Y | ety | — | — | 1 | comportamiento(noun,28,3), componer(verb,5,49), comportar(verb,4,3), comporta(noun,4,1), composición(noun,4,3) | **C** | prose 'Deverbal from comportar' (lemma ✓) |
| 55 | eros | noun | eros; sexual desire | 1.16 | Y | ety | — | 2/2 | 1 | — | **C** | related erótico/erógeno ✓; source ineligible (no form records); substring gate |
| 56 | incapacitado | adj | disabled; incapacitated | 1.16 | N | — | — | — | 0 | incapaz(adj,11,1), incapacidad(noun,2,5), incapacitar(verb,1,1), incapacitante(adj,0,1), incapacitación(noun,0,3) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 57 | Otelo | name | Othello (Shakespeare character) | 1.13 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 58 | ejecutor | noun | executor, administrator | 1.13 | Y | ety | — | — | 0 | ejecución(noun,13,3), ejecutivo(adj,10,6), ejecutivo(noun,10,6), ejecutar(verb,7,5), ejecutado(adj,5,1) | **D** | same-word entry in another family; no usable link evidence here |
| 59 | trombón | noun | trombone | 1.03 | Y | ety | 1/1+1w | 2/2 | 0 | trombosis(noun,1,2), tromba(noun,0,1), trombo(noun,0,6), trombocitopenia(noun,0,2), trombonista(noun,0,1) | **C** | derived trombonista ✓ + related tromba/trompa ✓ |
| 60 | dirigible | noun | dirigible | 1.03 | N | — | — | — | 0 | dirigir(verb,24,7), dirigido(adj,7,1), dirigente(adj,1,7), dirigente(noun,1,7), dirigencia(noun,0,4) | **B** | Wiktionary entry has no etymology and no derived/related lists |

### Band `0<f<1`

| # | word | pos | gloss | freq | etym | tpl | der | rel | syn | mates (≤5) | cls | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | touch | adj | touch; touch-screen | 0.88 | N | — | — | — | 0 | touchdown(noun,2,1), touché(adj,1,1), touchy(adj,0,1) | **A** | English loanword; mates touchdown/touché are English loans, not derivatives |
| 2 | neoyorquino | noun | a New Yorker; somebody from New York | 0.88 | Y | af | — | — | 0 | ~neoyorquino(adj,1,1) | **D** | af template (neo- + yorquino) has no lemma base; adj/noun pair and Nueva York sit in the DB with no connecting evidence |
| 3 | Lavandera | name | Lavandera: a surname | 0.64 | N | — | — | — | 0 | lavandería(noun,8,1), lavanda(noun,2,1), ~lavandera(noun,1,1), ~lavandera(noun,1,1), lavandero(noun,1,13) | **A** | proper noun — family-less expected |
| 4 | vodevil | noun | vaudeville | 0.54 | Y | ety | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 5 | toracotomía | noun | thoracotomy | 0.51 | Y | ety | — | — | 0 | torácico(adj,2,2), toracoscopia(noun,0,1), toracoabdominal(adj,0,5), toraco-(prefix,0,1), toracópodo(noun,0,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 6 | disecar | verb | to dissect | 0.51 | Y | ety | — | 2/2 | 0 | disección(noun,1,2), disecado(adj,1,1), disecado(noun,1,1), diseccionar(verb,0,2), disectar(verb,0,1) | **C** | related disección/segar ✓; substring gate; Latin etymon junk-regex-killed |
| 7 | cuscú | adj | nappy, frizzy | 0.38 | N | — | — | — | 0 | cuscús(noun,0,1), cuscuta(noun,0,1), cuscurro(noun,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 8 | Lacio | name | Lazio (an administrative region of Italy, situat… | 0.34 | Y | der | — | 2/2 | 0 | ~lacio(adj,0,3) | **A** | proper noun — family-less expected |
| 9 | chistera | noun | top hat | 0.33 | Y | bor+,der | — | — | 3 | chiste(noun,21,6), chistar(verb,21,1), chistoso(adj,4,6), chistoso(noun,4,6), chistero(noun,0,6) | **A** | borrowed from Basque; mate chiste is a false friend |
| 10 | colostomía | noun | colostomy | 0.30 | Y | af,bor+,der | — | — | 0 | colosal(adj,2,2), coloso(noun,1,2), Colosenses(name,0,1), Colosó(name,0,1), colosista(adj,0,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 11 | cabestrante | noun | capstan | 0.25 | Y | der | — | — | 0 | cabestrillo(noun,0,13), cabestro(noun,0,13), cabestrar(verb,0,13), cabestrear(verb,0,13) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 12 | lexicón | noun | lexicon | 0.22 | N | — | — | 1/1 | 0 | léxico(adj,0,3), léxico(noun,0,3), lexicógrafo(noun,0,1), léxicamente(adv,0,3), lexical(adj,0,1) | **C** | related léxico ✓; substring gate |
| 13 | Mayra | name | a female given name | 0.13 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 14 | devaneo | noun | idle pursuit, distraction or superficial pastime | 0.10 | Y | ety | — | — | 0 | devanar(verb,0,2), devanado(noun,0,1), devanagari(adj,0,1), devanagari(noun,0,1), devanadera(noun,0,2) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 15 | precognición | noun | precognition | 0.09 | N | — | — | — | 0 | precoz(adj,1,3), preconcebir(verb,0,5), preconcebido(adj,0,1), preconcepto(noun,0,1), precocinar(verb,0,4) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 16 | histrionismo | noun | exaggerated behaviour; histrionics, melodramatic… | 0.08 | N | — | — | — | 0 | histriónico(adj,0,1), histrión(noun,0,1), histricomorfo(noun,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 17 | Labán | name | Laban (Biblical character) | 0.06 | N | — | — | — | 0 | — | **A** | proper noun — family-less expected |
| 18 | despenar | verb | to put someone out of their misery | 0.06 | N | — | — | — | 0 | despertar(verb,61,7), despedir(verb,24,6), despedida(noun,24,1), despedido(adj,24,1), despertar(noun,21,7) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 19 | webmaster | noun | webmaster | 0.06 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 20 | sacrificial | adj | sacrificial | 0.05 | Y | ety | — | 2/2 | 0 | sacrificio(noun,17,2), sacrificar(verb,6,2), sacrificado(verb,4,1), sacrilegio(noun,1,1), sacristán(noun,1,1) | **C** | related sacrificar/sacrificio ✓; substring gate |
| 21 | llosa | noun | an enclosed arable land next to a house | 0.05 | Y | cog,ety | — | — | 0 | ~Llosa(name,0,1) | **D** | same-word entry in another family; no usable link evidence here |
| 22 | increpar | verb | to rebuke, to chastise | 0.04 | Y | bor+ | — | 1/1 | 0 | increíble(adj,152,2), increíblemente(adv,16,2), incremento(noun,2,4), incrementar(verb,2,4), incredulidad(noun,1,1) | **C** | related increpación ✓; substring gate |
| 23 | slender | adj | slender | 0.04 | Y | ety | — | — | 2 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 24 | Arriola | name | a surname from Basque | 0.04 | Y | bor+ | 1/1 | — | 0 | Arrio(name,0,1), arriostrar(verb,0,2), arriostramiento(noun,0,2), arriolismo(noun,0,1) | **A** | proper noun — family-less expected |
| 25 | incomparecencia | noun | no-show, failure to appear | 0.04 | N | — | — | — | 0 | incómodo(adj,17,2), incompetente(adj,3,1), incomodar(verb,3,1), incompetencia(noun,2,3), incomodo(noun,2,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 26 | buprenorfina | noun | buprenophrine | 0.04 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 27 | gombo | noun | gombo | 0.04 | N | — | — | 1/1 | 0 | — | **C** | related gombó ✓ — same lexeme, accent variant; RAW-string substring/word-group keys keep them apart |
| 28 | soportal | noun | porch | 0.04 | N | — | — | — | 0 | soportar(verb,31,5), soporte(noun,7,1), soportable(adj,1,5), sopor(noun,0,1), soporífero(adj,0,1) | **A** | from Latin sub portale; mate soportar (supportare) is a false friend |
| 29 | pantoque | noun | bilge | 0.03 | N | — | — | — | 0 | pantorrilla(noun,1,3), pantomima(noun,1,1), Pantoja(name,0,1), pantógrafo(noun,0,1), pantocrátor(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 30 | barcarola | noun | barcarole | 0.03 | N | — | — | — | 0 | barca(noun,5,14), barcaza(noun,1,1), barcada(noun,0,14), barcaje(noun,0,14) | **A** | borrowed from Italian; barca is the Italian-side relative, not a Spanish derivation |
| 31 | drogodependiente | noun | drug addict | 0.03 | N | — | — | — | 1 | drogo(adj,84,1), drogo(noun,84,1), drogodependencia(noun,0,4), drogota(noun,0,3) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 32 | presídium | noun | presidium | 0.03 | N | — | — | — | 0 | presidente(noun,144,6), presión(noun,58,5), presidenta(noun,13,1), presionar(verb,6,5), presidencial(adj,5,2) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 33 | rasgueado | noun | a guitar technique in which the fingers are unfu… | 0.03 | N | — | — | — | 0 | rasguño(noun,5,1), rasguñar(verb,5,1), rasgueo(noun,0,6), rasguear(verb,0,6), rasguido(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 34 | madriza | noun | beating, bashing | 0.02 | Y | — | — | — | 0 | Madrid(name,9,1), madrina(noun,4,20), madriguera(noun,2,1), madrigal(noun,0,1), madrileño(adj,0,3) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 35 | traedor | noun | bringer; bearer | 0.02 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 36 | domótico | adj | domotic | 0.02 | N | — | — | — | 0 | domótica(noun,0,1), domotización(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 37 | lacustre | adj | lake; lacustrine | 0.02 | Y | ety | — | — | 0 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 38 | limonera | noun | brimstone butterfly | 0.02 | N | — | — | — | 0 | Limón(name,9,1), limón(noun,9,3), limonada(noun,6,1), limonado(adj,6,1), limonero(noun,0,3) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 39 | mandarino | noun | mandarine tree | 0.02 | N | — | — | — | 0 | mandar(verb,49,14), manda(noun,22,1), mandado(noun,12,1), mandato(noun,4,2), mandatar(verb,4,2) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 40 | Elcano | name | a village in Navarre, Spain | 0.01 | Y | bor+ | — | — | 0 | — | **A** | proper noun — family-less expected |
| 41 | arrayán | noun | myrtle | 0.01 | Y | bor+ | 1/0 | — | 2 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 42 | birr | noun | birr (currency) | 0.01 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 43 | chicuelo | noun | kid; child | 0.01 | N | — | — | — | 0 | chicuela(noun,0,1), chicuelina(noun,0,1), chicura(noun,0,1), chicuate(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 44 | estatorreactor | noun | ramjet; athodyd | 0.01 | N | — | — | — | 0 | estatal(adj,13,8), estatua(noun,12,1), estatus(noun,4,1), estatura(noun,3,1), estática(noun,3,3) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 45 | Mitilene | name | Mytilene | 0.01 | N | — | — | — | 0 | Mitilini(name,0,1), mitileneo(adj,0,1), mitileneo(noun,0,1) | **A** | proper noun — family-less expected |
| 46 | anamita | adj | Annamite | 0.01 | N | — | — | — | 0 | ~anamita(noun,0,1) | **D** | same-word entry exists in another family; no etymological evidence here |
| 47 | hombrear | verb | to shoulder (push with the shoulder(s)) | 0.01 | Y | — | — | — | 0 | hombre(intj,1087,12), hombre(noun,1087,12), hombro(noun,22,3), hombría(noun,1,1), hombrecillo(noun,1,12) | **C** | prose 'From hombro' (lemma ✓) |
| 48 | Teodosia | name | a female given name | 0.01 | N | — | — | — | 0 | Teodoro(name,1,1), Teodora(name,0,1), Teodosio(name,0,1), teodolito(noun,0,1), Teodorico(name,0,1) | **A** | proper noun — family-less expected |
| 49 | replicativo | adj | replicative | 0.01 | N | — | — | — | 0 | réplica(noun,3,1), replicante(adj,1,5), replicante(noun,1,5), replicar(verb,1,5), replicador(noun,0,5) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 50 | salesa | noun | Salesian | 0.01 | N | — | — | — | 0 | Sales(name,24,1), salesiano(adj,0,1), salesiano(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 51 | libidinal | adj | libidinal | 0.00 | N | — | — | — | 0 | libido(noun,1,1), libidinoso(adj,0,1), libidinosidad(noun,0,1), libidinosamente(adv,0,1), libídine(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 52 | superfluidad | noun | superfluity | 0.00 | Y | ety | — | 1/1 | 0 | superior(adj,37,5), superior(noun,37,5), súper(adj,26,1), superficie(noun,24,4), super(adj,19,1) | **C** | related superfluo ✓; substring gate; Latin etymon junk-regex-killed |
| 53 | empeloto | adj | butt-naked; starkers | 0.00 | N | — | — | — | 0 | empellón(noun,0,2), empelar(verb,0,1), empellar(verb,0,1), empeller(verb,0,2), empellicar(verb,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 54 | esteño | noun | native or inhabitant of Ciudad del Este, Paragua… | 0.00 | Y | ety | — | — | 0 | estenosis(noun,0,1), estenógrafo(noun,0,1), estenografía(noun,0,1), estenopeico(adj,0,1), estentóreo(adj,0,1) | **C** | prose 'From (Ciudad del) Este + -eño' (base este exists as lemma) |
| 55 | gasón | noun | grass | 0.00 | Y | bor+,der,etymon | — | — | 2 | — | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 56 | hepatomegalia | noun | hepatomegaly | 0.00 | Y | ety | — | — | 0 | hepatitis(noun,2,1), hepática(noun,1,1), hepático(adj,1,2), hepatólogo(noun,0,1), hepatobiliar(adj,0,2) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 57 | olmeda | noun | elm grove | 0.00 | N | — | — | — | 0 | Olmedo(name,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 58 | pirren | verb | only used in se pirren, third-person plural pres… | 0.00 | N | — | — | — | 0 | pirre(verb,0,1), pirremos(verb,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 59 | sonetista | noun | sonnetist | 0.00 | N | — | — | — | 0 | soneto(noun,1,2), sonetico(noun,0,2) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 60 | videoenlace | noun | videolink | 0.00 | N | — | — | — | 0 | video(noun,43,4), videojuego(noun,5,5), videocámara(noun,1,17), videoclub(noun,0,3), videoconferencia(noun,0,7) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |

### Band `f==0`

| # | word | pos | gloss | freq | etym | tpl | der | rel | syn | mates (≤5) | cls | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | -crata | suffix | -crat | 0.00 | Y | bor+,der | — | 1/1 | 0 | -crático(suffix,0,1) | **A** | bound morpheme — not a family member |
| 2 | -grafía | suffix | -graphy | 0.00 | Y | bor+ | — | 3/3 | 0 | -gráfico(suffix,0,1), -grafo(suffix,0,1) | **A** | bound morpheme — not a family member |
| 3 | Corte Penal Internacional | name | International Criminal Court | 0.00 | N | — | — | — | 0 | corte(noun,84,5), corte(noun,84,5), Cortes(name,11,1), corten(intj,11,1), cortesía(noun,11,1) | **A** | multi-word expression — family-less expected |
| 4 | Serbia y Montenegro | name | Serbia and Montenegro (a former country in South… | 0.00 | N | — | — | — | 0 | Serbia(name,2,1), serbio(adj,2,1), serbio(noun,2,1), serbio(noun,1,1) | **A** | multi-word expression — family-less expected |
| 5 | aciforme | adj | aciform | 0.00 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 6 | actualista | noun | actualist | 0.00 | N | — | — | — | 0 | actuar(verb,44,4), actuación(noun,23,2), actual(adj,21,10), actual(noun,21,10), actualmente(adv,14,10) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 7 | adjetivo ordinal | noun | ordinal number (grammar: word used to denote rel… | 0.00 | N | — | — | — | 1 | adjetivo(adj,1,4), adjetivo(noun,1,1), adjetivar(verb,1,4), adjetival(adj,0,1), adjetivación(noun,0,4) | **A** | multi-word expression — family-less expected |
| 8 | alditol | noun | alditol | 0.00 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 9 | almatriche | noun | irrigation ditch | 0.00 | N | — | — | — | 0 | Almatý(name,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 10 | amor libre | noun | free love | 0.00 | N | — | — | — | 0 | amor al uso(noun,0,1), amor propio(noun,0,1), amor platónico(noun,0,1), amor prohibido(noun,0,1), amor del Canadá(noun,0,1) | **A** | multi-word expression — family-less expected |
| 11 | balandronada | noun | boastful behaviour | 0.00 | N | — | — | — | 0 | balance(noun,5,2), balanza(noun,3,8), balancear(verb,1,8), balanceo(noun,1,8), balanceado(adj,0,1) | **D** | transparent baladrón + -ada; baladrón exists in DB (4-char stem, below the proxy threshold) |
| 12 | bracarense | noun | native or inhabitant of Braga | 0.00 | N | — | — | — | 0 | Bracamonte(name,0,1), bracamante(noun,0,1), ~bracarense(adj,0,1), bracatinga(noun,0,1) | **D** | same-word entry exists in another family; no etymological evidence here |
| 13 | brazo armado | noun | A violent faction within a political group. | 0.00 | Y | lit,m-g,yesno | — | — | 0 | brazo(noun,60,10), brazola(noun,0,1), brazo de mar(noun,0,1), brazo de río(noun,0,1), brazo fuerte(noun,0,1) | **A** | multi-word expression — family-less expected |
| 14 | bróder | noun | bro (close friend) | 0.00 | Y | doublet,ety | — | — | 0 | — | **C** | doublet fraile ✓ — never loaded |
| 15 | caja de herramientas | noun | toolbox | 0.00 | N | — | — | — | 1 | caja boba(noun,0,1), caja china(noun,0,1), caja negra(noun,0,1), caja tonta(noun,0,1), caja fuerte(noun,0,1) | **A** | multi-word expression — family-less expected |
| 16 | calículo | noun | calyculus, calicle | 0.00 | Y | bor+ | — | — | 0 | calicó(noun,0,1), caliche(noun,0,1), calicanto(noun,0,1), calicreína(noun,0,1), calicata(noun,0,1) | **A** | no usable derivational evidence (atomic root / loanword / no derivatives recorded) |
| 17 | caracazo | noun | wave of violent protests and massacres, especial… | 0.00 | Y | ety | — | — | 0 | carácter(noun,18,2), característica(noun,5,2), característico(adj,5,1), caracol(noun,3,3), caracoles(intj,3,1) | **C** | suffix template Caracas + -azo; base Caracas is a name-pos lemma (ineligible E1 parent) |
| 18 | celtibérico | adj | Celtiberian | 0.00 | N | — | — | — | 0 | céltico(adj,0,1), celtiño(adj,0,1), celtiño(noun,0,1), celtismo(noun,0,4), celtista(adj,0,4) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 19 | centro de flores | noun | centrepiece (of flowers) | 0.00 | N | — | — | — | 0 | centro(noun,108,23), centrar(verb,108,3), Central(name,44,1), central(adj,44,17), central(noun,44,17) | **A** | multi-word expression — family-less expected |
| 20 | chaquense | noun | native or inhabitant of El Chaco Canton | 0.00 | N | — | — | — | 0 | chaqueta(noun,31,7), chaqueta(noun,31,7), chaquetón(noun,0,7), chaqué(noun,0,1), chaquetero(noun,0,7) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 21 | chichinguaste | noun | Mesosphaerum suaveolens | 0.00 | Y | der | — | — | 1 | chichón(adj,1,5), chichón(noun,1,5), chichi(adj,0,5), chichi(noun,0,5), chichi(noun,0,5) | **A** | Nahuatl loanword; der template names Nahuatl etymon only |
| 22 | cola de perro | noun | dog's-tail grass | 0.00 | N | — | — | — | 0 | cola de león(noun,0,1), cola de pato(noun,0,1), cola de rata(noun,0,1), cola de gallo(noun,0,1), cola de zorra(noun,0,1) | **A** | multi-word expression — family-less expected |
| 23 | comillas altas | noun | quotation marks (of the kind like “ ”) | 0.00 | N | — | — | — | 1 | comilla(noun,1,4), comilón(adj,0,2), comilón(noun,0,2), comilona(noun,0,1), comilla alta(noun,0,1) | **A** | multi-word expression — family-less expected |
| 24 | coosificarse | verb | coossify | 0.00 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 25 | cuitlacoche californiano | noun | California thrasher, Toxostoma redivivum. | 0.00 | N | — | — | — | 0 | cuitlacoche(noun,0,1), cuitlateco(adj,0,1), cuitlateco(noun,0,1), cuitlacoche rojizo(noun,0,1) | **A** | multi-word expression — family-less expected |
| 26 | delawareño | adj | Delawarean | 0.00 | N | — | — | — | 0 | Delaware(name,2,1), ~delawareño(noun,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 27 | desaminación | noun | deamination | 0.00 | N | — | — | — | 0 | desamparar(verb,1,4), Desamparados(name,1,1), desamor(noun,0,10), desamparo(noun,0,1), desamarrar(verb,0,5) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 28 | detroitino | noun | Detroiter (native or inhabitant of Detroit) (usu… | 0.00 | N | — | — | — | 0 | Detroit(name,7,1), ~detroitino(adj,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 29 | dosis de su propia medicina | noun | a taste of one's own medicine | 0.00 | Y | lit,m-g,yesno | — | — | 0 | dosis(noun,15,10) | **A** | multi-word expression — family-less expected |
| 30 | dígrafo | noun | digraph | 0.00 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 31 | echar las muelas | verb | to be hopping mad; to be in a massive rage | 0.00 | Y | lit,m-g,yesno | — | — | 0 | echar(verb,48,5), echarse al plato(verb,2,1), echar humo(verb,0,1), echar pata(verb,0,1), echar abajo(verb,0,1) | **A** | multi-word expression — family-less expected |
| 32 | en el día | adv | during the day, as opposed to at night | 0.00 | N | — | — | — | 1 | en ello(prep_phrase,0,1), en el ajo(adj,0,1), en el acto(adv,0,1), en el aire(adv,0,1), en el alma(adv,0,1) | **A** | multi-word expression — family-less expected |
| 33 | exhaustor | noun | exhauster | 0.00 | N | — | — | 8/6 | 0 | exhausto(adj,3,5), exhaustivo(adj,1,5), exhaustivamente(adv,0,5), exhaustividad(noun,0,5), exhaustación(noun,0,1) | **C** | related exhausto/exhaustivo/exhaustivamente/exhaustación/inexhausto/inexhaurible ✓; substring gate |
| 34 | folioso | adj | foliose | 0.00 | N | — | — | — | 0 | folio(noun,0,2), folíolo(noun,0,1), foliólulo(noun,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 35 | guama | noun | ice-cream bean | 0.00 | N | — | — | — | 1 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 36 | haloterapia | noun | halotherapy | 0.00 | N | — | — | — | 0 | halotano(noun,0,1), halotriquita(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 37 | hematocele | noun | hematocele | 0.00 | N | — | — | — | 0 | hematoma(noun,2,2), hematocrito(noun,0,1), hematología(noun,0,1), hematólogo(noun,0,1), hematíe(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 38 | hoy por hoy | adv | for the time being | 0.00 | N | — | — | — | 2 | hoy por ti, mañana po…(phrase,0,1) | **A** | multi-word expression — family-less expected |
| 39 | lluvia de ideas | noun | brainstorm | 0.00 | N | — | — | — | 0 | lluvia(noun,36,4), lluvioso(adj,1,4), lluviosidad(noun,0,1), lluvia ácida(noun,0,1), lluvia dorada(noun,0,1) | **A** | multi-word expression — family-less expected |
| 40 | mano negra | noun | cheating, funny stuff | 0.00 | N | — | — | — | 0 | mano dura(noun,0,1), mano a mano(adj,0,1), mano a mano(noun,0,1), mano de obra(noun,0,1), mano derecha(noun,0,1) | **A** | multi-word expression — family-less expected |
| 41 | monomarca | adj | single-brand | 0.00 | N | — | — | — | 0 | monomotor(adj,0,1), monómero(noun,0,1), monomanía(noun,0,1), monomito(noun,0,1), monomando(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 42 | numisma | noun | numisma | 0.00 | N | — | — | — | 0 | numismática(noun,0,1), numismático(adj,0,2), numismático(noun,0,2) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 43 | ojo del huracán | noun | eye of the storm | 0.00 | N | — | — | — | 0 | ojo de agua(noun,0,1), ojo de buey(noun,0,1), ojo de gato(noun,0,17), ojo derecho(noun,0,1), ojo de poeta(noun,0,1) | **A** | multi-word expression — family-less expected |
| 44 | pino canario | noun | The Canary Island pine, Pinus canariensis. | 0.00 | N | — | — | — | 1 | pino manso(noun,0,1), pino negro(noun,0,1), pino salado(noun,0,1), pino chileno(noun,0,1), pino acuático(noun,0,1) | **A** | multi-word expression — family-less expected |
| 45 | primo segundo | noun | second cousin | 0.00 | N | — | — | — | 0 | primo(adj,40,7), primo(noun,40,7), primo(noun,40,7), primo(noun,40,7), primordial(adj,2,2) | **A** | multi-word expression — family-less expected |
| 46 | profrancés | adj | pro-French | 0.00 | N | — | — | — | 0 | profranquista(adj,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 47 | quiera que no | adv | like it or lump it | 0.00 | N | — | — | — | 0 | quier(conj,0,1), quiera Dios(adv,0,1), quiero decir(phrase,0,1), quieras que no(adv,0,1) | **A** | multi-word expression — family-less expected |
| 48 | recifeño | adj | of, from or relating to Recife | 0.00 | Y | ety | — | — | 0 | Recife(name,0,1), ~recifeño(noun,0,1) | **C** | suffix template Recife + -eño; base Recife is a name-pos lemma (ineligible E1 parent) |
| 49 | registraduría | noun | registry | 0.00 | N | — | — | — | 0 | registro(noun,37,7), registrar(verb,37,7), registrador(noun,2,7), registración(noun,0,1), registral(adj,0,7) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 50 | reoxidación | noun | reoxidation | 0.00 | N | — | — | — | 0 | reoxigenar(verb,0,2) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 51 | santaniano | noun | native or inhabitant of San Estanislao (usually … | 0.00 | N | — | — | — | 0 | Santa(adj,57,1), santa(noun,57,13), Santana(name,2,1), Santana(name,2,1), Santander(name,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 52 | seríceo | adj | sericious | 0.00 | N | — | — | — | 0 | sérico(adj,0,1), sericina(noun,0,1), sericícola(adj,0,1), sericultura(noun,0,1), sericicultor(adj,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 53 | sobremontado | adj | surmounted | 0.00 | N | — | — | — | 0 | sobre(noun,1129,9), sobre(prep,1129,9), sobrevivir(verb,37,30), sobredosis(noun,8,10), sobreviviente(adj,7,30) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 54 | tocuyano | adj | of, from or relating to El Tocuyo | 0.00 | N | — | — | — | 0 | ~tocuyano(noun,0,1) | **D** | same-word entry exists in another family; no etymological evidence here |
| 55 | toque de diana | noun | reveille | 0.00 | N | — | — | — | 1 | toque(noun,39,2), toquetear(verb,0,1), toqueteo(noun,0,1), toquegua(adj,0,1), toquegua(noun,0,1) | **A** | multi-word expression — family-less expected |
| 56 | trogocitosis | noun | trogocytosis | 0.00 | N | — | — | — | 0 | trogón(noun,0,1) | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 57 | uniflagelado | adj | uniflagellate | 0.00 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |
| 58 | vacacionable | adj | suitable for a vacation | 0.00 | N | — | — | — | 0 | vacación(noun,59,2), vacacionar(verb,59,1), vacacional(adj,0,2), vacacionista(noun,0,1) | **D** | plausible relative(s) sit in the DB; this entry has no dictionary evidence at all |
| 59 | zambullidor orejudo | noun | black-necked grebe | 0.00 | N | — | — | — | 0 | zambullir(verb,1,11), zambullida(noun,1,1), zambullidor(noun,0,11), zambutir(verb,0,1), zamburiña(noun,0,1) | **A** | multi-word expression — family-less expected |
| 60 | zolpidén | noun | zolpidem | 0.00 | N | — | — | — | 0 | — | **B** | Wiktionary entry has no etymology and no derived/related lists |

## 2.1 Per-band class distributions

| band | n | A | B | C | D |
|---|---|---|---|---|---|
| 10<=f<100 | 60 | 27 | 8 | 20 | 5 |
| 1<=f<10 | 60 | 22 | 10 | 16 | 12 |
| 0<f<1 | 60 | 23 | 19 | 8 | 10 |
| f==0 | 60 | 26 | 18 | 4 | 12 |
| sample total | 240 | 98 | 55 | 48 | 39 |

The sample C items (48) are listed in §1.2-style form in §2.2.

## 2.2 The 48 sample-band C items

- **substring** (14):
  - **principio** (noun, freq 92.50, band 10<=f<100) — related principiante/principiar ✓; substring gate
  - **construir** (verb, freq 34.66, band 10<=f<100) — related construcción/constructivo/constructor ✓; substring gate
  - **tripulación** (noun, freq 23.16, band 10<=f<100) — related tripulante/tripular ✓; substring gate
  - **auxilio** (noun, freq 16.33, band 10<=f<100) — related auxiliar ✓; substring gate
  - **dificultad** (noun, freq 11.76, band 10<=f<100) — related difícil ✓; substring gate
  - **nómina** (noun, freq 3.27, band 1<=f<10) — related nombre ✓ (Latin nomen family); substring gate
  - **depredador** (noun, freq 3.12, band 1<=f<10) — related depredar ✓ (depredar + -dor); substring gate
  - **pediatra** (noun, freq 1.89, band 1<=f<10) — related pediatría/pediátrico ✓; substring gate
  - **adoptivo** (adj, freq 1.80, band 1<=f<10) — related adopción/adoptar ✓; substring gate
  - **mástil** (noun, freq 1.72, band 1<=f<10) — related mastelero ✓ (mástel + -ero); substring gate
  - **lexicón** (noun, freq 0.22, band 0<f<1) — related léxico ✓; substring gate
  - **sacrificial** (adj, freq 0.05, band 0<f<1) — related sacrificar/sacrificio ✓; substring gate
  - **increpar** (verb, freq 0.04, band 0<f<1) — related increpación ✓; substring gate
  - **exhaustor** (noun, freq 0.00, band f==0) — related exhausto/exhaustivo/exhaustivamente/exhaustación/inexhausto/inexhaurible ✓; substring gate
- **prose-parent** (12):
  - **indio** (noun, freq 35.16, band 10<=f<100) — prose 'From India' (lemma ✓, name)
  - **limpia** (noun, freq 31.99, band 10<=f<100) — prose 'Deverbal from limpiar' (lemma ✓, family of 8)
  - **súper** (adj, freq 25.85, band 10<=f<100) — prose 'From super' (lemma ✓) — accent-variant homograph; RAW-string word-group keys keep them apart
  - **aprecio** (noun, freq 23.91, band 10<=f<100) — prose 'Deverbal from apreciar' (lemma ✓)
  - **güey** (noun, freq 14.99, band 10<=f<100) — etymology text names Spanish parent buey (pronunciation variant, lemma ✓); prose-only, no template
  - **criado** (noun, freq 10.48, band 10<=f<100) — prose 'Past participle of criar' (lemma ✓)
  - **cierro** (noun, freq 5.87, band 1<=f<10) — prose 'Deverbal from cerrar' (lemma ✓)
  - **referente** (noun, freq 2.28, band 1<=f<10) — prose 'From referir' (lemma ✓)
  - **tranqui** (adj, freq 1.22, band 1<=f<10) — ety template 'Clipping of tranquilo' (lemma ✓, family of 6); clipping link not extracted
  - **comporte** (noun, freq 1.19, band 1<=f<10) — prose 'Deverbal from comportar' (lemma ✓)
  - **hombrear** (verb, freq 0.01, band 0<f<1) — prose 'From hombro' (lemma ✓)
  - **esteño** (noun, freq 0.00, band 0<f<1) — prose 'From (Ciudad del) Este + -eño' (base este exists as lemma)
- **doublet-unloaded** (6):
  - **té** (noun, freq 75.71, band 10<=f<100) — doublet cha ✓ — never loaded
  - **armario** (noun, freq 29.45, band 10<=f<100) — doublet armero ✓ — never loaded
  - **confundir** (verb, freq 16.16, band 10<=f<100) — doublet cohonder ✓ + related confusión ✓
  - **cesar** (verb, freq 5.08, band 1<=f<10) — doublet cejar ✓ + derived cesamiento/cesante/cesantía/cese ✓
  - **hostal** (noun, freq 1.50, band 1<=f<10) — doublet hospital ✓ + related hospital/huésped ✓
  - **bróder** (noun, freq 0.00, band f==0) — doublet fraile ✓ — never loaded
- **substring+junk-regex** (3):
  - **acceder** (verb, freq 10.38, band 10<=f<100) — related acceso/accesible/accesión/accesar ✓; substring gate; Latin etymon junk-regex-killed
  - **disecar** (verb, freq 0.51, band 0<f<1) — related disección/segar ✓; substring gate; Latin etymon junk-regex-killed
  - **superfluidad** (noun, freq 0.00, band 0<f<1) — related superfluo ✓; substring gate; Latin etymon junk-regex-killed
- **parent-ineligible(name)** (2):
  - **caracazo** (noun, freq 0.00, band f==0) — suffix template Caracas + -azo; base Caracas is a name-pos lemma (ineligible E1 parent)
  - **recifeño** (adj, freq 0.00, band f==0) — suffix template Recife + -eño; base Recife is a name-pos lemma (ineligible E1 parent)
- **substring+surf-unparsed** (2):
  - **continuación** (noun, freq 17.53, band 10<=f<100) — related continuar ✓ + 'surf' template continuar + -ción (unparsed); substring gate
  - **motocicleta** (noun, freq 6.31, band 1<=f<10) — related motociclismo ✓; 'surf' (surface-analysis) template moto- + bicicleta is not parsed; substring gate
- **src-ineligible(adv)** (1):
  - **delante** (adv, freq 91.89, band 10<=f<100) — derived adelante/delantal ✓ + related antes ✓; source adv has no forms
- **substring+allomorph** (1):
  - **risa** (noun, freq 18.54, band 10<=f<100) — related reír ✓ + sonrisa ✓ ('sonrisa' contains 'risa', substring passes); E4b allomorph gate blocks sonrisa (does not START with risa)
- **raw-string-variant** (1):
  - **gombo** (noun, freq 0.04, band 0<f<1) — related gombó ✓ — same lexeme, accent variant; RAW-string substring/word-group keys keep them apart
- **src-ineligible(no-forms)+substring** (1):
  - **eros** (noun, freq 1.16, band 1<=f<10) — related erótico/erógeno ✓; source ineligible (no form records); substring gate
- **substring+prose-parent** (1):
  - **proveniente** (adj, freq 1.32, band 1<=f<10) — related proveniencia ✓ + prose 'From provenir' (lemma ✓, family of 56)
- **E4-gates** (1):
  - **prodigio** (noun, freq 2.51, band 1<=f<10) — derived prodigioso ✓; E4 gates
- **E4-gates+substring** (1):
  - **trombón** (noun, freq 1.03, band 1<=f<10) — derived trombonista ✓ + related tromba/trompa ✓
- **src-ineligible(no-forms)** (1):
  - **izquierda** (noun, freq 81.81, band 10<=f<100) — derived izquierdista ✓; source ineligible: no form records; Basque etymon → no Latin roots for E4
- **allomorph-prefix-strip+prose-parent** (1):
  - **empleado** (noun, freq 22.07, band 10<=f<100) — related empleador ✓ — substring passes; allomorph gate blocks because strip_one_prefix('empleador')='pleador' (fossilized em- stripped as if a Spanish prefix); prose 'Past participle of emplear' (lemma ✓)


## 3. The ceiling — what happens if every C is fixed

Extrapolation: for each band, the C-rate measured on the audited set (exact for the 367; sample-based for
the other four) is applied to that band's full singleton count, with Wilson 95% confidence intervals on the
sample rates. Fixing a C removes exactly one singleton (it joins an existing family).

| band | singletons | audited | C found | C-rate (Wilson 95%) | singletons rescued | singleton rate now | rate after all-C |
|---|---|---|---|---|---|---|---|
| freq >= 100 | 367 | 367 (all) | 77 | 21.0% (exact) | 77 | 32.5% | **25.7%** |
| 10 <= freq < 100 | 1,242 | 60 | 20 | 33.3% [22.7%, 45.9%] | 282–571 | 29.9% | **20.0%** (mid) |
| 1 <= freq < 10 | 4,586 | 60 | 16 | 26.7% [17.1%, 39.0%] | 786–1,789 | 41.5% | **30.5%** (mid) |
| 0 < freq < 1 | 30,145 | 60 | 8 | 13.3% [6.9%, 24.2%] | 2,084–7,285 | 57.8% | **50.1%** (mid) |
| freq == 0 | 41,272 | 60 | 4 | 6.7% [2.6%, 15.9%] | 1,082–6,573 | 84.7% | **79.0%** (mid) |
| **all** | **77,612** | 607 | 125 | — | **≈10,300 (4,312–16,294)** | **66.2%** | **≈57.4% (52.3%–62.5%)** |

**If every scrap of usable evidence were extracted (fixing all 125 itemised C cases), the overall singleton
rate would fall from 66.2% to roughly 57% (95% CI 52–63%) — not to 40%.** The 0<f<1 and f==0 bands,
which hold 92% of all singletons, have the lowest C-rates (13% and 7%): most of their singletons are
B (no etymology at all) and A (atomic), which no extraction work can move.

Two further splits of the same arithmetic:

- **Extraction bugs only** (the 59 C items that need no design decision — junk-regex, doublet-unloaded,
  unparsed template types, prose parents, raw-string keys, empty-affix, `-e` reject):
  overall rate falls to **≈62%** (95% CI 59–65%). Per band the bug-only rescue rates are
  hi 10.9%, 10≤f<100 15.0% [8.1–26.1%], 1≤f<10 10.0% [4.7–20.1%], 0<f<1 5.0% [1.7–13.7%], f==0 1.7% [0.3–8.9%].
- **Gate reconsideration** (the 66 C items blocked by a deliberate precision/eligibility gate — the E4b
  substring gate, E4 shared-root-keys, adverb/invariable source eligibility, closed-class/name parents) is
  required for the rest of the gap down to ~57%.

**Bottom line: the realistic ceiling is ~60%, not 40%.** Even perfect extraction leaves a majority of
families-of-one intact, because for most singletons Wiktionary simply records nothing linkable (B) or the
word is genuinely atomic (A).

## 4. Two specific sub-questions

### 4a — synonyms on the 367 high-frequency singletons

- **113 of 367 (30.8%)** have at least one synonym recorded in Wiktionary (top-level or sense-level).
- Their entries carry 265 synonym items, of which 216 are single words and **198 of those exist as lemmas
  in the DB** (91.7% — a synonym feature would almost always land on a clickable entry).
- If you decline to show semantic relations, you are declining coverage for about **one third** of the
  high-frequency singleton pages, concentrated in ordinary content words (e.g. *error* → equivocación,
  yerro; *qué* → cuál; *sí* → simón; *para* → hacia, a).

### 4b — how singleton-ness breaks down by POS

Over all 77,612 singletons:

| group | singletons | share |
|---|---|---|
| expected classes (name, intj, prep, conj, det, article, pron, particle, num) | **9,112** | 11.7% |
| content words (noun, verb, adj, adv) | **66,824** | 86.1% |
| other (suffix, prefix, phrase, proverb, prep_phrase, contraction, adv_phrase) | **1,676** | 2.2% |

Only 11.7% of singletons are in POS classes where being family-less is expected. **86% of the singleton
problem is content words** — the vast majority of them nouns (45,179) and adjectives (13,517).


## 5. Systemic findings (the mechanisms behind the C list)

1. **The junk-ancestor regex kills `ety`-tree etymologies.** `_JUNK_ANCESTOR_RE = [()<>,]|\s|[0-9]` rejects
   ancestors like `niger<alt:nigrum>` because wiktextract's modern `ety` template stores the displayed form
   inline (`args["3"] = "la:niger<alt:nigrum>"`). Every entry whose etymology is wrapped in an `ety`-tree
   template therefore ends up with **no ancestors at all**: no E3 root-key edges, no E4 shared-root gate,
   no E5 homograph merge. Reproduced with a mini-builder: the three `negro` entries (adj, noun×2) parse to
   the identical etymon yet sit in three different families. Fix: strip `<[^>]*>` from the ancestor before
   the junk test (the same cleanup already applied to template args elsewhere). Measured in the audited
   set: ~18/607 entries have *all* their etymons junk-killed (`negro`, `error`, `abogar`, `acceder`,
   `confundir`, `construir`, `continuación`, `disecar`, `superfluidad`, `ejecutor`, `Marte`, …).
2. **`doublet`/`dbt` templates are parsed in `build.py` and then discarded** — `doublet_edges` is collected but
   `FamilyBuilder` has no loader for it. 14 of the 607 audited singletons have a doublet twin that exists as
   a lemma (`era`↔área, `auto`↔acto, `sino`↔signo, `dama`↔dueña, `haz`↔facies, `luego`↔locus, `vetar`↔vedar,
   `abogar`↔advocar, `té`↔cha, `confundir`↔cohonder, `armario`↔armero, `cesar`↔cejar, `hostal`↔hospital,
   `bróder`↔fraile).
3. **Etymology prose naming a Spanish parent is never parsed.** `Deverbal from probar`, `Past participle of
   querer`, `Clipping of tranquilo`, `From cual + quiera`, `Back-formation from ama` — the single biggest C
   category in the high band (23 of 77). `parse_templates` only reads tree-shaped prose lines; a plain
   "From X" sentence is invisible. A pattern-based extractor (`From X`, `Deverbal from X`, `Past participle
   of X`, `Clipping of X`, `Back-formation from X`, `See X`) with a lemma-existence check would rescue all
   of these.
4. **Template types wiktextract emits that E1 has no case for:** `surf` ("By surface analysis, X + -ar"),
   `prothetic form`, `back-form`, `abbrev`, and `ety`-wrapped `clipping`. Each names a Spanish base that
   exists as a lemma (`tranquilar` ← tranquilo, `dentrar` ← entrar/dentro, `amo` ← ama, `A` ← alfil,
   `tranqui` ← tranquilo).
5. **`deverbal` templates produce an empty affix** (`prueba` ← `probar + ''`) and E1 skips empty-affix edges
   by design — the deverbal relation itself is lost.
6. **The derivational suffix `-e` is in E1's inflectional-desinence reject list** (`niñe` ← niña + -e), so the
   whole gender-neutral `-e` derivation family (niñe, amigue, tíe, hermane, xadre, aliade…) is unreachable.
7. **RAW-case string keys.** E4b's substring gate compares `word.lower()` without accent folding, and E5's
   word groups are keyed by the raw word. Accent-variant pairs (`aún`/`aun`, `gombo`/`gombó`, `súper`/`super`,
   `dónde`/`donde`) can therefore never merge even though their folded forms are identical.
8. **`rid <= lid` ordering drops asymmetric derived/related lists.** E4/E4b visit each unordered pair once,
   from the listing side; when the listed target has a *smaller* lemma id than the listing source, the pair
   is never visited and the edge is silently lost (e.g. `puntar`→`apuntar`; `hija`→`hijo`; part of the
   `negro`→`negrillo` stack).
9. **Adverbs and invariable words have no form records in Wiktionary**, which makes them ineligible as
   E4/E4b sources and as E1 parents — even though the E1 README already allows ineligible *children*. A
   targeted change (allow ineligible sources in E4/E4b, or allow form-less adverbs as E1 parents) would
   rescue the `anoche`/`así`/`dentro`/`fuera`/`arriba`/`acerca`/`delante`/`encima`/`dónde`/`afuera` cluster.
10. **Closed-class and proper-noun bases** (`Dios` for `adiós`, `Caracas` for `caracazo`, `Recife` for
    `recifeño`, `más` for `demás`) are ineligible as E1 parents, even though ineligible lemmas are allowed
    as family *members*. Allowing them as parents (the head would still be a content word) rescues these.

## 6. Boundary cases deliberately left OUT of C (conservatism notes)

- Closed-class/name entries whose entry carries real derivational evidence were classified **A** (expected to
  be family-less), but the evidence exists and is unused: `de` (derived: dequeísmo, dacá, del, della…),
  `con` (conque, conmigo, consigo, contigo, connosco, convusco), `la` (laísmo), `tres` (tercia, tercio,
  trece, treinta, terciario), `uno` (doublet un), `vos` (vosear, voseo), `tú` (tutear, tuteo), `usted`
  (ustedear, ustedeo), `hasta`/`donde`/`sí` (homograph sets whose E5 merge is blocked only because no member
  is eligible to head the family). If these were counted as C, the hi-band C-rate would rise from 21% to
  ~24%.
- `siempreviva` has an affix template naming `siempre`, but the multi-component compound rule attaches the
  compound to the *last* base (`viva`) only — `siempre` stays out by design (kept as D).
- Related-list items that are NOT genuine relatives were rejected as C: `ir`→andar/caminar/ser/marchar
  (synonyms), `este`→oriental (different root), `mesar`→atusar, `ambo`→ambos, `jamás`→más/ya, `lord`→milord,
  `té`→infusión, `güey`→vato.
- Where I could not tell, I classified down (C only when both the evidence and the target lemma were
  verified); the A/B/D boundary within the non-actionable set carries judgment calls recorded in the table.

## 7. Reproducibility

- `recon/singleton_audit.py` — streams the JSONL once, reads the DB read-only, emits the two JSON files.
- `recon/singleton_audit_targets.json` — the 607 audited lemmas with prefix mates.
- `recon/singleton_audit_evidence.json` — per-lemma etymology/derived/related/synonym evidence.
- `recon/singleton_audit_classification.json` — final A/B/C/D classification with reasons.
- Sample seed: `random.Random(42)` over each band's sorted singleton pool.

