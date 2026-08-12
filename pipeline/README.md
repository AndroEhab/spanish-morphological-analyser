# Pipeline — Morphological Family Construction

The family algorithm builds a graph of Spanish lemmas and extracts connected components as morphological families. Each family is a set of words sharing a Latin root, Spanish-internal derivation, or verb conjugation paradigm.

## Edge Types

Five edge types connect lemmas in the admission graph, applied in order:

### E1 — Affix Edges
Spanish-internal affixation: `des- + hacer → deshacer`, `hacer + -dor → hacedor`, `que + hacer → quehacer`.

**Gates:**
- Both endpoints must pass the eligibility predicate (non-closed POS, has forms, not a synonym/alternative-form gloss).
- Internal degree ≤ 50, E1 degree ≤ 30.
- Compound rule (J2): when a lemma has ≥2 eligible bare-component parents, pick one — prefer the verb, else longest word, tie-break alphabetically. Non-selected parents are skipped.
- Latin provenance filter: for bare-component compounds only (not prefixes/suffixes), skip the edge if the child has Latin ancestors whose root keys do not overlap the parent's. This prevents false derivations like `estable < estar + -able` when `estable` is inherited from Latin `stabilis`.
- Affix string must be non-empty.

**Labels:** `prefix- + base`, `base + -suffix`, `prefix + base` (bare component). Known Spanish prefixes get a hyphen even when the template omits it (`contra- + hacer`). Circumfixes render as `prefix- + base + -suffix`.

**E1 eligibility note:** The eligibility predicate is only required of the
*parent* endpoint for E1 edges.  Ineligible children (e.g. adverbs that
carry no forms in Wiktionary) can still receive E1 edges from eligible
parents.  This is how `-mente` adverbs join their adjective's family.

**Form-based component resolution:** When an affix template's base component
does not resolve to a lemma (e.g. `sola` in `sola + -mente`), the builder
looks it up in the form table.  If the component is a known inflected form of
exactly one lemma — or one candidate lemma has a stronger POS match — that
lemma is used as the endpoint.  This repairs derivations whose base is cited
in an inflected form.

**Template arg normalization:** wiktextract cites the affix of
`suffix`/`suf`/`prefix`/`pre` templates WITHOUT a hyphen (`casa + ero`,
`bi + cameral`), unlike `af`/`affix` which hyphenate it.  The parser
normalizes the bare suffix/prefix arg of those four template names to a
hyphenated form so it is recognized as an affix instead of a second bare
component.  Without this, `casero`'s `suffix` template (`casa + ero`) parses
as a compound with base `ero` and the edge never forms.

**Positional-arg hygiene:** only pure-numeric template args are treated as
components; named args (`gloss1`, `id2`, `alt1`, `t1`, …) are dropped.
Before this, `embotellamiento`'s template `{suffix|es|embotellar|gloss1=…|3=miento}`
parsed with `miento` as a bare second base, which the form table then
resolved to the lemma `mentir`, producing the garbage edge
`mentir + embotellar`.

**Identity-based affix recognition:** in affix templates, a bare component
is recognized as an affix by membership in a closed inventory of Spanish
derivational suffixes (`-miento, -ción, -sión, -dor, -dora, -ero, -era,
-ería, -ista, -ismo, -idad, -edad, -anza, -encia, -ancia, -aje, -azo,
-ada, -ado, -ura, -ble, -ible, -able, -oso, -osa, -illo, -illa, -ito,
-ita, -ón, -ona, -uelo, -eño, -ense, -ico, -al, -ar, -orio, -ivo, -ante,
-ente, -mente`) and prefixes (`des-, re-, contra-, anti-, in-, …`), not
only by position.  Two guards keep bases safe: a bare component is not a
prefix when the last component is already hyphenated (`auto + -dromo`:
`auto` is the base), and not a suffix when the first component was
hyphenated in the source (`anti- + edad`, `re- + bien`: the remaining
bare word is the base).  With ≥3 components both may fire
(`en- + red + -ar`, `geo- + centro + -ismo`); with exactly 2 at most one.

**Form-table resolution guards:** when a template base is not a lemma, the
form table is consulted to repair bases cited in an inflected form
(`sola → solo`, `manos → mano`).  Four guards contain it:
- Exact word matches outrank accent-folded ones (`baja` wins over `bajá`,
  `mano` over `maño`) — template bases are accent-free (`camara → cámara`).
- A word in the base slot that IS a derivational affix by identity never
  resolves (`miento` is a suffix, not a base — it must never become
  `mentir`).
- Capitalized bases (place/person names) resolve only to a case/plural
  variant of themselves (`Newton → newton`, `Tortugas → tortuga`), never
  to a similarly spelled verb (`Aspe → aspar`, `Muño → munir`).
- With several distinct candidate lemmas, only inflectional variants of
  the cited base are accepted (`ceda` vs `ceder`/`cerda` resolves to
  nothing; `seguida → seguido`, `follado → follar`).  A lemma never
  resolves to itself as parent.

### E2 — Paradigm Edges
Verbs sharing the same conjugation residual key are connected if they are derivationally related.

**Gates (all three required):**
1. `residual_key(C) == residual_key(H)` — same paradigm bucket.
2. `len(P_C) > len(P_H)` — the compound must have a strictly longer stem prefix.
3. `P_C.endswith(P_H)` — prefix containment, OR the two verbs share a Latin root key (any), OR the compound is in the head's derived list.

**Bucket cap:** Only paradigm buckets with ≤40 members are family-forming. Larger buckets (the regular `-ar`/`-er`/`-ir` classes, thousands of verbs) carry no family information and are excluded.

### E3 — Root-Key Edges
Words whose Latin ancestors share a computed root key are connected. The Latin root key is `first5` of the ancestor (after stripping Latin prefixes) plus, for verb-shaped ancestors, a supine key `first3 + "T"`.

**Note — truncated stems deliberately REJECTED here:** the E4/E4b gates
admit truncated citation stems as allomorphs (see below), but E3 does NOT.
Truncation was measured for E3 and rejected: rescue precision was ~60%
(computed supine-T keys collide with truncated stems — `beleño ↔
belenismo` via `belen`, `carecer ↔ careo` via `care`, `barracuda ↔ barro`
via `barT`), versus ~97% for E4/E4b.  Do not re-add truncated stems to the
E3 allomorph set.


**Additional gates:**
- Both words must not be in `borrowed_lemmas`.
- Allomorph overlap: one word's stripped form must start with a ≥3-char allomorph of the other.
- First4 overlap: the two words' Latin ancestors must share a first4 prefix. This prevents unrelated words from connecting solely through a shared supine T-key (e.g., `pono` and `pontus` both produce `ponT` but are different Latin words).

### E4 — Derived Edges
Words listed in each other's `derived` field from Wiktionary. Additionally requires shared Latin root keys — the allomorph test alone is not enough, as Wiktionary's "derived" sections mix in antonyms and compounds that bridge unrelated Latin roots.

**Truncated-stem allomorphs:** for the allomorph test, E4 (and E4b) also
admit the accent-folded citation form minus a final `-a`/`-o`/`-e`, bounded
by `_MIN_TRUNC_STEM` (4).  Spanish derivation drops the theme vowel
(`cámara → camar-` in `camarero`), which the plain citation form can never
match.  The truncated stem is a FILTER on the dictionary's own derived/
related lists, never a generator.  It is deliberately NOT admitted by E3:
measured rescue precision there was ~60% (computed supine-T keys collide
with truncated stems — `beleño ↔ belenismo` via `belen`), versus ~97% for
E4/E4b.

### E4b — Related Edges (Substring-Gated)
Words in each other's `related` field may create an edge ONLY if one word's citation form contains the other as a substring. `mentira` contains `mentir` → edge created. `mente` does not contain `mentir` → excluded. This prevents the `related` field (which lists etymologically adjacent but distinct words) from chaining unrelated families.

### E5 — POS Homograph Edges
Two lemma entries with the same `word` that share an etymology must land in
the same family.  This merges the adjective, adverb, noun, and interjection
entries of a single lexeme (e.g. `rápido` adj + `rápido` adv + `rápido`
noun).  Entries with `pos = 'name'` (proper nouns) are excluded — they are
not content-word homographs.

**Gate:** overlapping ancestor sets, OR one entry has no etymology of its own
(kaikki routinely omits etymology on the secondary POS of a single lexeme).
Never merge on spelling alone: entries whose ancestors don't overlap AND both
have some etymology data (ancestors or internal derivation) remain separate
(e.g. `haz` < `fascis` vs `haz` < `facies`).

**Labels:** from the member's own POS perspective, e.g. the adverb entry
reads `adv use of rápido`, the noun entry `noun use of rápido`.

## Eligibility Predicate
A lemma is eligible if:
- POS is not in `_CLOSED_POS` (conj, pron, prep, det, article, particle, num, intj, suffix, prefix, interfix, infix, name, phrase, proverb, prep_phrase, adv_phrase).
- Folded word is not in `_FUNC_STOPLIST`.
- Has at least one form record.
- Gloss does not start with "synonym", "alternative form/spelling", "obsolete form/spelling", "misspelling", "superseded spelling", "archaic form", "eye dialect", or "inflection of".

Ineligible lemmas can be members of families (edges to them are allowed) but cannot be family heads.

## Head Selection
Within each component, the eligible lemma that minimizes
`(has_e1_parent, POS-order, -frequency, word_length, -affix_degree, word)`
is the family head.  Members with no E1 parent inside the component are
strongly preferred — the derivational base (e.g. `rápido`) wins over the
derived noun (`rapidez`).  Among roots, the ordering continues.  POS order:
verb(0) < adj(1) < noun(2) < adv(3) < other(99).  The shortest verb is
virtually always the base: `poner` over `imponer`, `hacer` over `deshacer`.

## BFS Label Assignment
BFS computes depths for all members. Each non-head member selects the best incoming edge from neighbors at **strictly smaller depth** — self-referential labels are structurally impossible. Candidates rank by: edge-type precedence (affix 0 > paradigm 1 > root-key 2 > derived 3 > homograph 4), then neighbor depth, then neighbor citation form. For `root-key` labels, the member's own Latin ancestor is used; Spanish words in ancestor lists are filtered out.

## Worked Example: The `hacer` Family

`hacer` (verb) ← Latin `facere` (root keys: `facer`, `facT`).

| Member | POS | Edge | Why In |
|--------|-----|------|--------|
| hacer | verb | root | head |
| deshacer | verb | E1 affix | `des- + hacer` |
| rehacer | verb | E1 affix | `re- + hacer` |
| satisfacer | verb | E2 paradigm | same residual key; `satisfac` contains `hac` |
| contrahacer | verb | E1 affix | `contra- + hacer` |
| hacedor | noun | E1 affix | `hacer + -dor` |
| hacedero | adj | E1 affix | `hacer + -dero` |
| quehacer | noun | E1 affix | `que + hacer` |
| hechura | noun | E3 root-key | ← Latin `factura`; shares `facT` with `facere`; first4 `fact` ∩ `faci` |
| hechor | noun | E3 root-key | ← Latin `factor`; shares `facT` with `facere` |
| malhechor | noun | E3 root-key | ← Latin `malefactorem`; shares `facT` |
| bienhechor | noun | E3 root-key | ← Latin `benefactorem`; shares `facT` |
| hecho | adj/noun | E3 root-key | ← Latin `factus`/`factum`; shares `facT` |
| hechizo | adj/noun | E3 root-key | ← Latin `facticius`; shares `facT` |
| hechizar | verb | E1 affix | `hechizo + -ar` |
| hechicero | adj/noun | E1 affix | `hechizo + -ero` |
| hechicería | noun | E1 affix | `hechizo + -ería` |
| hacienda | noun | E3 root-key | ← Latin `facienda`; shares `facT`/`fazT` |
| hacendar | verb | E1 affix | `hacienda + -ar` |
| hacendado | adj/noun | E1 affix | `hacendar + -ado` |

**Why `hechura` is in:** Latin `factura` → `facT` (supine key from `tura`). Latin `facere` → `facT` (from verb `ere`). Shared `facT` + first4 overlap (`fact` vs `faci` — no, but `facio` → `faci` and `factura` → `fact`; first4 `fact` vs `faci` → no direct overlap, but `facio` and `facienda` share `faci`... actually the chain is through `facT` supine + first4 `faci` from `facienda`/`facio`).

**Why `factura` is out:** `factura` (Spanish) is a learned borrowing from Latin, not inherited. Its etymon mode is "borrowed", so it enters `borrowed_lemmas` and is excluded from E3 (root-key edges). Even if it had an E1 edge, the Latin provenance filter would block it since `factura`'s own Latin ancestors don't overlap with the parent's.

**Why `malhecho` is out:** Zero etymology data in wiktextract — no templates, no text, no derived/related links. Genuinely unreachable from the source data.


## Accepted Data Limitations

Two well-understood gaps are accepted as inherent to the source data:

- **`malhecho`** — zero etymology data in wiktextract: no templates, no text,
  no derived/related links.  Genuinely unreachable from the source and always
  excluded from the `hacer` family.
- **`lentitud`** — classified as a Latin borrowing (`:bor` from
  `lentitūdō`) rather than Spanish-internal `lento + -tud`.  Borrowed lemmas
  are excluded from E3 root-key edges, and the E4b substring gate blocks the
  `related` link because the stem changes (`lent-` vs `lento`).  It remains
  outside `lento`'s family.