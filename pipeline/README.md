# Pipeline — Morphological Family Construction

The family algorithm builds a graph of Spanish lemmas and extracts connected components as morphological families. Each family is a set of words sharing a Latin root, Spanish-internal derivation, or verb conjugation paradigm.

## Edge Types

Six edge types connect lemmas in the admission graph, applied in order:

### E1 — Affix Edges
Spanish-internal affixation: `des- + hacer → deshacer`, `hacer + -dor → hacedor`, `que + hacer → quehacer`.

**Gates:**
- The parent must pass the membership predicate (content POS, not stoplisted, non-redirect gloss). Form rows are NOT required — an adverb without forms can be a parent (`a- + fuera → afuera`).
- Internal degree ≤ 50, E1 degree ≤ 30.
- Compound rule (J2): when a lemma has ≥2 eligible bare-component parents, pick one — prefer the verb, else longest word, tie-break alphabetically. Non-selected parents are skipped.
- Latin provenance filter: for bare-component compounds only (not prefixes/suffixes), skip the edge if the child has Latin ancestors whose root keys do not overlap the parent's. This prevents false derivations like `estable < estar + -able` when `estable` is inherited from Latin `stabilis`.
- Affix string must be non-empty.
- Inflectional desinences are rejected as affixes (`-á -é -í -ó -ió -a -o -aba -ara -iera -ase -iese -are -iere`). `-e` is NOT rejected — it is the gender-neutral derivational suffix (`niñe = niña + -e`); `-ía` is NOT rejected either — it is the abstract-noun suffix (`demasía = demás + -ía`, `alegría = alegre + -ía`).

**Labels:** `prefix- + base`, `base + -suffix`, `prefix + base` (bare component). Known Spanish prefixes get a hyphen even when the template omits it (`contra- + hacer`). Circumfixes render as `prefix- + base + -suffix`.

**Form-based component resolution:** when an affix template's base component does not resolve to a lemma (e.g. `sola` in `sola + -mente`), the builder looks it up in the form table. If the component is a known inflected form of exactly one lemma — or one candidate lemma has a stronger POS match — that lemma is used as the endpoint. This repairs derivations whose base is cited in an inflected form.

**Template arg normalization:** wiktextract cites the affix of `suffix`/`suf`/`prefix`/`pre`/`surf` templates WITHOUT a hyphen (`casa + ero`, `bi + cameral`), unlike `af`/`affix` which hyphenate it. The parser normalizes the bare suffix/prefix arg of those template names to a hyphenated form so it is recognized as an affix instead of a second bare component.

**Positional-arg hygiene:** only pure-numeric template args are treated as components; named args (`gloss1`, `id2`, `alt1`, `t1`, …) are dropped. Before this, `embotellamiento`'s template `{suffix|es|embotellar|gloss1=…|3=miento}` parsed with `miento` as a bare second base, which the form table then resolved to the lemma `mentir`, producing the garbage edge `mentir + embotellar`.

**Identity-based affix recognition:** in affix templates, a bare component is recognized as an affix by membership in a closed inventory of Spanish derivational suffixes and prefixes, not only by position. Two guards keep bases safe: a bare component is not a prefix when the last component is already hyphenated (`auto + -dromo`: `auto` is the base), and not a suffix when the first component was hyphenated in the source (`anti- + edad`, `re- + bien`: the remaining bare word is the base). With ≥3 components both may fire (`en- + red + -ar`, `geo- + centro + -ismo`); with exactly 2 at most one.

**Form-table resolution guards:** when a template base is not a lemma, the form table is consulted to repair bases cited in an inflected form (`sola → solo`, `manos → mano`). Four guards contain it:
- Exact word matches outrank accent-folded ones (`baja` wins over `bajá`, `mano` over `maño`).
- A word in the base slot that IS a derivational affix by identity never resolves (`miento` is a suffix, not a base — it must never become `mentir`).
- Capitalized bases (place/person names) resolve only to a case/plural variant of themselves (`Newton → newton`, `Tortugas → tortuga`), never to a similarly spelled verb (`Aspe → aspar`, `Muño → munir`).
- With several distinct candidate lemmas, only inflectional variants of the cited base are accepted. A lemma never resolves to itself as parent.

### E2 — Paradigm Edges
Verbs sharing the same conjugation residual key are connected if they are derivationally related.

**Gates (all three required):**
1. `residual_key(C) == residual_key(H)` — same paradigm bucket.
2. `len(P_C) > len(P_H)` — the compound must have a strictly longer stem prefix.
3. `P_C.endswith(P_H)` — prefix containment, OR the two verbs share a Latin root key (any), OR the compound is in the head's derived list.

**Bucket cap:** Only paradigm buckets with ≤40 members are family-forming. Larger buckets (the regular `-ar`/`-er`/`-ir` classes, thousands of verbs) carry no family information and are excluded.

### Prose Edges — Explicit Parentage Statements
Admitted kinds assert parentage explicitly: `deverbal from X`, `clipping of X`, `past participle of X`, `back-formation from X`, `abbreviation of X`, `prothetic form of X`, `univerbation of X`, `inflection of X`.  These rank above computed root-key matches but below affix templates: `affix > paradigm > prose > root-key > derived`.

The bare `From X` sentence (kind `from`) is admitted ONLY through the
two-gate design used everywhere else in this system: the sentence is the
evidence of connection, an allomorph test is the precision filter.  A
`from`/`variant` candidate becomes an edge only when the named parent
resolves to an existing Spanish lemma AND the two citation forms share a
≥4-character allomorph (one accent-folded form starts with a ≥4-char
allomorph of the other, after at most one Spanish-prefix strip).
`gracias`/`gracia` share `graci`; `querida`/`querer` share `quer`; a vague
cognate or semantic influence almost never shares a 4-char stem and is
rejected.

**Deliberately NOT sources:**
- Etymology-tree "Spanish X" lines — they mix in affixes (`Spanish -eco` for Chiapas + -eco) and component words that collide with unrelated modern homographs (the tree of `hijo` names Old Spanish `fijo`, which would resolve to the unrelated modern lemma `fijo` "fixed").
- Affix-shaped parents (`From narco- (“drugs”) + policía`) — the bare form would resolve to an unrelated homograph; only a sentence-final `From super-.` survives.
- The `+`-continuation of "From X + Y" — it names a suffix, whose bare form resolves to an unrelated homograph (`ismo` "ism", `ario` "Aryan", `auto` "car").
- Doublet templates — see below.

**Compound guard:** a prose edge is skipped when the parent is a component of the child's own compound (bare or hyphenated affix — `matar` in `mata + ojos`, `tele-` in `tele- + tienda`).  The J2 mirror: a compound attaches to its last base via E1 and must not re-attach its other components.

**Labels** name the relation: `deverbal from probar`, `clipping of automóvil`, `back-formation from ama`, `past participle of querer`, `from gracia`, `prothetic form of entrar`.

### E3 — Root-Key Edges
Words whose Latin ancestors share a computed root key are connected. The Latin root key is `first5` of the ancestor (after stripping Latin prefixes) plus, for verb-shaped ancestors, a supine key `first3 + "T"`.

**Latin-only keys:** root keys are generated ONLY from `la*`-language ancestors. Old Spanish citations (`osp "libro"`, `osp "librar"`) are Spanish words — deriving Latin supine keys from them makes `liber` "book" and `liberare` "free" collide and merges `libro` with the free-family.

**Truncated stems deliberately REJECTED here:** the E4/E4b gates admit truncated citation stems as allomorphs (see below), but E3 does NOT. Truncation was measured for E3 and rejected: rescue precision was ~60% (computed supine-T keys collide with truncated stems), versus ~97% for E4/E4b. Do not re-add truncated stems to the E3 allomorph set.

**Additional gates:**
- Both words must not be in `borrowed_lemmas`.
- Allomorph overlap: one word's stripped form must start with a ≥3-char allomorph of the other.
- First4 overlap: the two words' Latin ancestors must share a first4 prefix. This prevents unrelated words from connecting solely through a shared supine T-key (e.g., `pono` and `pontus` both produce `ponT` but are different Latin words).

### E4 — Derived Edges
Words listed in each other's `derived` field from Wiktionary. Additionally requires shared Latin root keys — the allomorph test alone is not enough, as Wiktionary's "derived" sections mix in antonyms and compounds that bridge unrelated Latin roots.

**No id-ordering condition:** derived/related lists are per-lemma and asymmetric — every listed pair is visited regardless of lemma-id order (previously pairs with `rid <= lid` were silently dropped).

**Compound guard:** same J2 mirror as prose — a derived item that is a bare component of the child's own compound (`matar` in `mataojos = mata + ojos`) is skipped.

**Truncated-stem allomorphs:** for the allomorph test, E4 (and E4b) also admit the accent-folded citation form minus a final `-a`/`-o`/`-e`, bounded by `_MIN_TRUNC_STEM` (4). Spanish derivation drops the theme vowel (`cámara → camar-` in `camarero`), which the plain citation form can never match. The truncated stem is a FILTER on the dictionary's own derived/related lists, never a generator. It is deliberately NOT admitted by E3.

### E4b — Related Edges
Words in each other's `related` field may create an edge when any of these hold:

- **(a) Accent variant** — same folded spelling (`aún`/`aun`, `gombo`/`gombó`, `dónde`/`donde`).
- **(b) Substring containment AND allomorph prefix** — one citation form contains the other AND the target starts with a source stem. This pair of gates stops `mentir ↔ mente` ("mente" starts with "ment" but neither citation contains the other) and `bien ↔ bienhechor` ("bien" is stripped as a Spanish prefix before the allomorph test).
- **(c) Strict inflectional pair** — one word equals the other plus a single trailing character (`gracias`/`gracia`), or an equal-length pair differing only in the final 1–2 characters (`hija`/`hijo`). Deliberately stricter than the form-table's rank test, whose 2-vs-1 drops admit `mentir`/`mente` through the 4-char stem "ment".
- **(d) Shared Latin root key** — exact non-supine overlap of any-mode ancestor keys, with two hard restrictions: the pair must have DISJOINT ancestor sets (a pair sharing the SAME exact etymon — `ir`/`ser` both citing `esse` — is a suppletion or synonym chain, not a derivation), and the branch is disabled when one citation contains the other (a compound component cannot re-enter through root keys). Prefix-level key matches are deliberately rejected: `sentire`/`sedentare` (`sentir`/`sentar`) collide at first3 AND first4, so any looser test re-bridges unrelated roots. Cost: `ley`↔`legal` cannot connect — the real etymons `legem`/`legalis` differ at the 4th character and every looser test provably admits `sentir`↔`sentar`.

### E5 — POS Homograph Edges
Two lemma entries with the same `word` that share an etymology must land in the same family. The POS exclusion does NOT apply here — merging a word with itself can never introduce a bridge. Entries with `pos = 'name'` (proper nouns) are excluded — they are not content-word homographs.
## Head Selection
The head is the member that is a transitive ancestor of the most other
members in the directed graph of E1 (affix) and prose parent edges — the
word everything else was built from.  Tie-break: frequency desc, then
shortest citation form, then word asc.  In a pure root-key/E5 cluster with
no directed edges, the tie-break (frequency, then length) applies directly.
The head must additionally pass head eligibility: content POS and at least
one form row.

## Eligibility
- Gloss does not start with "synonym", "alternative form/spelling", "obsolete form/spelling", "misspelling", "superseded spelling", "archaic form", "eye dialect", or "inflection of".

**Form rows are NOT required for membership** — invariable words and form-less adverbs (`gracias`, `así`, `fuera`, `dentro`, `arriba`, `encima`, `acerca`, `anoche`, `izquierda`, `eros`) are real family members.

**Closed-class POSes** (`conj, pron, prep, det, article, particle, num, intj, name`) may be non-E5 edge endpoints but are **capped at degree 1**: only their single best edge is kept, by relation precedence (affix > paradigm > prose > root-key > derived). A degree-1 leaf cannot bridge two families — this replaces the old blanket exclusion, under which `gracias`/`adiós`/`demás`/`afuera` could never link to anything, not even their own homograph.

**Heads** additionally require: content POS (not closed-class) AND at least one form row.

## Doublets — deliberately NOT edges
`doublet`/`dbt` templates pair a learned borrowing with its inherited twin (`factura ↔ hechura`, `era ↔ área`, `sino ↔ signo`). This is exactly the pattern the `hacer` cutoff excludes: loading doublets would pull `factura` into `hacer`'s family through `hechura`, and gating them by root keys re-bridges the same borrowings. Any borrowed-side exclusion kills the wanted cases too (`era ↔ área` has a borrowed side). Doublets stay parsed-but-unloaded; the related 14 audit items are re-classified as non-actionable, not fixed.


## BFS Label Assignment
BFS computes depths for all members. Each non-head member selects the best incoming edge from neighbors at **strictly smaller depth** — self-referential labels are structurally impossible. Candidates rank by: edge-type precedence (affix 0 > paradigm 1 > prose 2 > root-key 3 > derived 4 > homograph 5), then neighbor depth, then neighbor citation form. For `root-key` labels, the member's own Latin ancestor is used; Spanish words in ancestor lists are filtered out.

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

**Why `hechura` is in:** Latin `factura` → `facT` (supine key from `tura`). Latin `facere` → `facT` (from verb `ere`). Shared `facT` + first4 overlap.

**Why `factura` is out:** `factura` (Spanish) is a learned borrowing from Latin, not inherited. Its etymon mode is "borrowed", so it enters `borrowed_lemmas` and is excluded from E3 (root-key edges). Even if it had an E1 edge, the Latin provenance filter would block it since `factura`'s own Latin ancestors don't overlap with the parent's.

**Why `malhecho` is out:** Zero etymology data in wiktextract — no templates, no text, no derived/related links. Genuinely unreachable from the source data.

## Etymon & Derivation Tables (the ancestry layer)

The build persists two display-only tables alongside the four core ones; the API's derivation map, ancestry ribbon and cousins strip read them. **They never feed back into family membership, root keys, or any edge type.**

- **`etymon`** — the parsed ancestor chain per lemma: `(lemma_id, depth, lang, lang_label, word, norm, norm_root, mode, note)`. `depth` 0 is the immediate ancestor, increasing back in time. `word` is as written in the source (macrons preserved); `norm` is the accent/macron-stripped lowercase join key. `note` records a decomposition only when the source states one ("ad + illīc" — 4 rows in the whole corpus; it is nearly always NULL). Template etymons (`inh`/`bor`/`der`/`ety`/`etymon`/`root`) come first in parse order, then etymology-tree entries in reverse (root-to-leaf tree order ⇒ the last tree line is the immediate ancestor); rows are deduplicated by `(norm, lang, mode)`. Proto-language rows and reconstructed forms are kept in the table but are **never join keys**.
- **`derivation`** — the BFS tree the label assignment already computes, persisted instead of thrown away: `(child_id PRIMARY KEY, parent_id, relation, label)`. Exactly one row per non-head family member; none for heads.

**`norm_root` — the prefix-stripped secondary join key.** Most Spanish words cite a *prefixed* Latin reflex rather than the root itself (`objetar < obiectāre`, `proyectar < prōiectāre`, `inyectar < iniectāre`, `sujetar < subiectāre`, `desechar < disiectāre`), so an exact-`norm` join rarely connects them. `norm_root` is `norm` with at most one Latin prefix stripped, using the same closed `_LATIN_PREFIXES` list `_latin_root_keys` uses — `obiectare → iectare`, `proiectare → iectare`, `disiectare → iectare`, and `echar` already carries `iectare`. The cousins API joins on `norm` first (exact shared etymon, strongest signal); when that yields nothing usable it falls back to `norm_root`.

**Fan-out cap.** A shared etymon with more than 60 Spanish descendants is too generic to be a "cousins" signal (`mens` alone has 2,536; 37 norms exceed 60 counting all rows, 6 among non-proto join keys) — the API drops to the next-deepest etymon, and if none qualifies it returns `cousins: null`. The same cap applies to `norm_root`; only 6 stripped roots exceed it.

**⚠️ `norm_root` is display-only.** It is persisted for the cousins lookup and must never be reused as a family-membership key, a root key, or an edge generator. The `hacer` cutoff (learned `yect-`/`jet-` vs inherited `ech-`) is deliberate: `proyectar` showing up as a *cousin* of `objetar` is correct; merging their families would not be. If a future feature wants a "same root" edge, it needs its own gated design — do not shortcut it through `norm_root`.

- **`english_cognate`** — the English side of the `englishRelatives` card (Phase 3): one row per (English lemma word, cited Latin `norm`) for every English lemma entry citing a Latin-family etymon, from one streaming pass over the English kaikki edition. A module-level assertion pins it outside the five core tables and the family builder never reads it; the build fills it only after families are finalised. Join filters (measured in docs/COGNATES_FEASIBILITY.md — option (b), 95.0% strict on the post-refinement audit): the pipeline's `is_usable_ancestor`, pure-ASCII-alpha norms, the observed language-code leak set, a closed blocklist of Latin preposition/prefix words (`trans`, `ante`, `contra`, `post`, … — prefix-only citations are not root relations), and English bound-morpheme/phrase POS excluded. Rows keep the gloss of the entry that cited the norm, so merged homographs (`peel` < `pala` vs `peel` < `pilare`) display the sense that matched. The API joins on `norm` first and `norm_root` as the fallback channel with the same 60-descendant fan-out cap as cousins; the table is additive and never influences family membership, root keys, or any edge type.

## Accepted Data Limitations

- **`conducir`'s family is headed by `producir`.**  The `-ducir` verbs are
  Latin borrowings (`producir` < `producere`) with no Spanish-internal
  affix edge to `ducir`, so no member dominates `producir` by descendant
  count under the head rule and `producir` — the more frequent word —
  legitimately wins.  Accepted: the head rule is correct, the family is
  correct, only the head word differs from the pre-closure build.
- **`fuera`'s family is headed by `forastero`.**  `fuera` (adv) carries
  zero Wiktionary form rows, so it fails head eligibility (forms are
  required of heads by design); among form-bearing members `forastero`
  wins the frequency tie-break.  `afuera`, `afueras`, `afuerino` and
  `afuerear` are all correctly merged into that family.
- **Bare `from X` and `variant of X` prose** are admitted only through
  the allomorph gate (§Prose Edges).  `güey`→`buey` fails it and stays a
  singleton; accepted.
- **Template mode markers are never components.**  `:calque`/`:inh`/
  `:bor`-style args in affix templates are skipped — before this guard,
  `televisión`'s `:calque` arg parsed as the base word "calque" and
  form-resolved to `calcar`, bridging the shoe/trace family into
  `televisión`'s.
- **Label integrity assertions** run at build time and cover every
  relation: paradigm/derived labels may never splice the head word inside
  a token, and every affix label must name its actual parent (an edge
  endpoint) as one of its ` + ` parts.

Well-understood gaps accepted as inherent to the source data:

