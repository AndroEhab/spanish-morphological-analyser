"""Family construction — connected components of a strictly-gated admission graph.

Consolidated rewrite. Edge rules: E1 (affix), E2 (paradigm), E3 (root-key), E4 (derived).
Families = connected components. Ancestors only from structured templates, never prose trees.
"""

from __future__ import annotations

from collections import defaultdict
import re as _re

from pipeline.normalize import fold, accent_strip
from pipeline.paradigm import compute_allomorphs, strip_one_prefix, get_family_forming_buckets, compute_paradigm_key, build_paradigm_buckets
from pipeline.etymology import _DERIV_SUFFIXES, _DERIV_PREFIXES



# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

_SPANISH_PREFIXES = sorted([
    "des", "re", "con", "contra", "en", "em", "entre", "mal", "bien",
    "sobre", "sub", "super", "tras", "trans", "pre", "pro", "ante",
    "anti", "in", "im", "ex", "extra", "per", "satis", "semi",
    "auto", "co", "circun", "inter", "intra", "retro", "ultra", "vice",
    "pos", "post",
], key=len, reverse=True)

_LATIN_PREFIXES = sorted([
    "male", "bene", "satis", "dis", "de", "re", "con", "com", "co",
    "ex", "ef", "in", "im", "per", "prae", "pre", "pro", "ad", "af",
    "ob", "sub", "sur", "trans", "tra", "circum", "inter", "intra",
    "retro", "super", "ne", "se",
], key=len, reverse=True)

_ETYMON_HUB = 400
_ROOT_KEY_HUB = 400
_MAX_INTERNAL_DEGREE = 50
_MAX_E1_DEGREE = 30
_MAX_BUCKET = 40
# Minimum length of a truncated non-verb citation stem admitted to the
# allomorph filter (E3/E4 gates).  Spanish derivation drops the final theme
# vowel (cámara → camar- in camarero), but the truncated form is ONLY a
# filter on independently-evidenced candidates, never an edge generator.
_MIN_TRUNC_STEM = 4

_BANNED_LANGS = frozenset({
    "ine-pro", "itc-pro", "gem-pro", "cel-pro", "grk-pro",
    "sla-pro", "bat-pro", "ine", "qfa-sub", "sem-pro", "afa-pro",
})

_JUNK_ANCESTOR_RE = _re.compile(r'[()<>,]|\s|[0-9]')
_LATIN_VERB_RE = _re.compile(r'(re|o|io|are|ere|ire|ari|iri)$')
_LATIN_NOMINAL_RE = _re.compile(
    r'(ndus|nda|ndum|ndo|tura|tus|ta|tum|tor|torem|tio|tionem|ticius|tivus|tilis|bilis|men|mentum|trix)$')

# Closed-class content POSes: allowed as non-E5 edge endpoints but capped at
# degree 1 (a leaf cannot bridge).  Bound morphemes and multi-word
# expressions never take edges at all.
_CAP_POS = frozenset({
    "conj", "pron", "prep", "det", "article", "particle",
    "num", "intj", "name",
})
_BOUND_POS = frozenset({
    "suffix", "prefix", "interfix", "infix",
    "phrase", "proverb", "prep_phrase", "adv_phrase",
    "character", "punct", "symbol",
})
_CLOSED_POS = _CAP_POS | _BOUND_POS

_FUNC_STOPLIST = frozenset({
    "que", "no", "se", "lo", "la", "le", "me", "te", "nos", "os",
    "y", "o", "a", "de", "en", "por", "para", "con", "sin", "al",
    "del", "es", "si", "ya", "mas", "muy", "tan",
})
# Note: mal and bien are NOT in the stoplist — they are content-bearing.


def _is_usable_ancestor(word: str, lang: str | None, mode: str | None) -> bool:
    if mode == "root":
        return False
    if word.startswith("*"):
        return False
    if lang and (lang in _BANNED_LANGS or lang.endswith("-pro")):
        return False
    if _JUNK_ANCESTOR_RE.search(word):
        return False
    if word.startswith("-") or word.endswith("-"):
        return False
    if len(word) < 3:
        return False
    return True


def _is_latin_ancestor(word: str, lang: str | None) -> bool:
    if lang:
        latins = {"la", "la-lat", "la-eme", "la-med", "la-vul", "la-ecc", "la-new",
                  "osp", "es", "fro", "frm", "fr", "it", "pt", "ca", "oc"}
        return lang in latins
    return len(word) >= 3 and not word.startswith("-")


def _latin_root_keys(word: str) -> list[str]:
    w = word.lower()
    for pfx in _LATIN_PREFIXES:
        if w.startswith(pfx) and len(w) > len(pfx) + 2:
            w = w[len(pfx):]
            break
    keys = []
    if len(w) >= 5:
        keys.append(w[:5])
    elif len(w) >= 4:
        keys.append(w[:4])
    if len(w) >= 4 and (_LATIN_VERB_RE.search(w) or _LATIN_NOMINAL_RE.search(w)):
        keys.append(w[:3] + "T")
    return keys


def _latin_first4_set(ancestors: set) -> set:
    """Return the set of first4 prefixes from Latin ancestors (stripped of Latin prefixes)."""
    result = set()
    for anc in ancestors:
        if not _is_latin_ancestor(anc, None):
            continue
        w = anc.lower()
        for pfx in _LATIN_PREFIXES:
            if w.startswith(pfx) and len(w) > len(pfx) + 2:
                w = w[len(pfx):]
                break
        if len(w) >= 4:
            result.add(w[:4])
    return result


def _allomorphs_for_gates(word: str, pos: str, forms: list) -> set[str]:
    """Allomorph set used by the E4/E4b (derived/related) admission gates.

    Extends compute_allomorphs with the truncated citation stem
    (accent-folded word minus a final -a/-o/-e), bounded by _MIN_TRUNC_STEM.
    Spanish derivation systematically drops the theme vowel (cámara →
    camar- in camarero), and the truncated form admits such derivatives
    through the allomorph test.  It is strictly a FILTER on candidates
    evidenced by the dictionary's own derived/related word lists — it never
    generates edges by itself.  It is deliberately NOT used by the E3
    root-key gate, whose computed-key evidence collides with truncated
    stems (measured rescue precision ~60% there vs ~97% here).
    """
    stems = compute_allomorphs(word, pos, forms)
    if pos != "verb":
        folded = accent_strip(word).lower()
        if folded.endswith(("a", "o", "e")) and len(folded) - 1 >= _MIN_TRUNC_STEM:
            stems = set(stems)
            stems.add(folded[:-1])
    return stems


def _inflectional_variant_rank(base: str, cit: str) -> int:
    """Rank how plausibly `base` is an inflected form of `cit` (2 > 1 > 0).

    Compares both after dropping 0-2 final characters: rank 2 on an exact
    (accent-preserving) match, rank 1 on an accent-folded match.  Symmetric
    drops (i == j, e.g. seguida->seguido, sola->solo) need >=3 shared
    characters; asymmetric drops (ceda->ceder) need >=4 — short form
    homographs that are not inflectional variants fail with rank 0 and are
    not resolved.
    """
    for rank, folded in ((2, False), (1, True)):
        b = accent_strip(base).lower() if folded else base
        c = accent_strip(cit).lower() if folded else cit
        for i in range(3):
            bpart = b[:-i] if i else b
            for j in range(3):
                cpart = c[:-j] if j else c
                if bpart != cpart:
                    continue
                if i == j:
                    if len(bpart) >= 3:
                        return rank
                elif len(bpart) >= 4 or (i == 1 and j == 0 and len(bpart) >= 3):
                    return rank
    return 0


def _is_inflectional_pair(a: str, b: str) -> bool:
    """Strict plural/gender variant test for the E4b gate.

    Admits one word equalling the other plus a single trailing character
    (gracias/gracia) and equal-length pairs sharing everything but their
    final 1-2 characters (hija/hijo).  Deliberately stricter than
    _inflectional_variant_rank, whose 2-vs-1 drops admit mentir/mente
    through the 4-char stem "ment".
    """
    la, lb = len(a), len(b)
    if abs(la - lb) == 1:
        long, short = (a, b) if la > lb else (b, a)
        if long[:-1] == short:
            return True
    if la == lb:
        for d in (1, 2):
            if a[:-d] == b[:-d] and len(a) - d >= 3:
                return True
    return False

def _regenerate_affix_label(rlabel: str, ref_word: str) -> str:
    """Given an affix rlabel like 'des- + hacer', replace the reference word."""
    parts = rlabel.split(" + ", 1)
    if len(parts) != 2:
        return rlabel
    left, right = parts
    if left.endswith("-"):
        return f"{left} + {ref_word}"
    elif right.startswith("-"):
        return f"{ref_word} + {right}"
    elif left.rstrip("-") in _SPANISH_PREFIXES:
        return f"{left}- + {ref_word}"
    else:
        return f"{left} + {ref_word}" if len(left) < len(right) else f"{ref_word} + {left}"


# ----------------------------------------------------------------------------
# FamilyBuilder
# ----------------------------------------------------------------------------

class FamilyBuilder:
    def __init__(self):
        self.lemmas: dict[int, dict] = {}
        self.internal_children: dict[int, list[tuple[int, str]]] = defaultdict(list)
        self.internal_parents: dict[int, list[tuple[int, str]]] = defaultdict(list)
        self.internal_degree: dict[int, int] = defaultdict(int)

        self.etymon_index: dict[str, set[int]] = defaultdict(set)
        self.lemma_ancestors: dict[int, set[str]] = defaultdict(set)
        self.lemma_etymon_modes: dict[int, set[str]] = defaultdict(set)
        self.borrowed_lemmas: set[int] = set()

        self.root_key_index: dict[str, set[int]] = defaultdict(set)
        self.ancestor_langs: dict[int, dict[str, str]] = defaultdict(dict)

        self.lemma_bucket: dict[int, tuple] = {}
        self.lemma_prefix: dict[int, str] = {}
        self.family_forming_buckets: dict[tuple, set[int]] = {}

        self.derived_links: dict[int, list[str]] = defaultdict(list)
        self.related_links: dict[int, list[str]] = defaultdict(list)
        self.word_index: dict[str, list[int]] = defaultdict(list)
        self.form_to_lemmas: dict[str, set[int]] = defaultdict(set)

        self.hub_etymons: set[str] = set()
        self.hub_root_keys: set[str] = set()

        self.inh_root_keys: dict[int, set[str]] = defaultdict(set)
        self.prose_parents: dict[int, list[tuple[int, str]]] = defaultdict(list)


        self.families: dict[int, dict] = {}
        self.family_of: dict[int, int] = {}

    def load_lemmas(self, records):
        for rec in records:
            lid = rec["id"]
            self.lemmas[lid] = rec
            self.word_index[fold(rec["word"])].append(lid)
            for fobj in rec.get("forms", []):
                if isinstance(fobj, dict):
                    fw = fobj.get("form", "")
                    if fw and len(fw) >= 2:
                        self.form_to_lemmas[fold(fw)].add(lid)

    def load_internal_edges(self, edges):
        for e in edges:
            cid = e["lemma_id"]
            pw = e["parent_word"]
            affix = e.get("affix", "")
            pids_raw = self.word_index.get(fold(pw), [])
            # Prefer EXACT word matches; fall back to accent-folded matches
            # (template bases are routinely cited accent-free: "camara" ->
            # cámara).  Exact-first keeps folded homographs from winning J2
            # tie-breaks on codepoint order (baja vs bajá, mano vs maño).
            exact = [p for p in pids_raw if self.lemmas[p]["word"] == pw]
            pids = exact or [p for p in pids_raw
                             if accent_strip(self.lemmas[p]["word"]) == accent_strip(pw)]
            if not pids:
                # A derivational affix cited in the base slot must never
                # resolve through the form table: "miento" is a suffix, not
                # a base — resolving it to the lemma "mentir" produces
                # nonsense edges like "mentir + embotellar".  Form-table
                # resolution exists to find a genuine derivational base
                # cited in an inflected form (sola → solo); affix-shaped
                # words are excluded from it by identity, and capitalized
                if accent_strip(pw).lower() in _DERIV_SUFFIXES | _DERIV_PREFIXES:
                    continue
                # Resolve component through form table when it is not a lemma
                # (e.g. feminine form cited as base for -mente adverb).
                form_pids = self.form_to_lemmas.get(fold(pw), set())
                if pw[:1].isupper():
                    # Capitalized bases are place/person names.  They may
                    # resolve only to a case/plural variant of themselves
                    # (Newton -> newton, Tortugas -> tortuga), never to a
                    # similarly spelled verb (Aspe -> aspar, Muño -> munir).
                    lpw = accent_strip(pw).lower()
                    ok = [p for p in form_pids
                          if accent_strip(self.lemmas[p]["word"]).lower() == lpw
                          or (lpw.endswith("s")
                              and accent_strip(self.lemmas[p]["word"]).lower() == lpw[:-1])]
                    form_pids = set(ok) if ok else set()
                if len(form_pids) == 1:
                    pids = list(form_pids)
                elif len(form_pids) > 1:
                    cites = {self.lemmas[p]["word"] for p in form_pids}
                    if len(cites) == 1:
                        # Same word, multiple POS entries: legacy choice.
                        cands = [p for p in form_pids if self.lemmas[p].get("pos") != "adv"] or list(form_pids)
                    else:
                        # Heterogeneous form homographs: accept only
                        # inflectional variants of the cited base
                        # (sola→solo, manos→mano, follado→follar).
                        # Non-variants (ceda vs ceder/cerda) must not
                        # resolve at all.  Exact matches outrank
                        # accent-folded ones (mano over maño).
                        ranks = [(p, _inflectional_variant_rank(pw, self.lemmas[p]["word"]))
                                 for p in form_pids]
                        best_rank = max(r for _, r in ranks)
                        cands = [p for p, r in ranks if r == best_rank] if best_rank > 0 else []
                    if len(cands) == 1:
                        pids = list(cands)
                    elif len(cands) > 1:
                        # Ambiguous: prefer candidates with non-adv POS (the
                        # base of an adverb is almost never an adverb itself).
                        non_adv = [p for p in cands if self.lemmas[p].get("pos") != "adv"] or cands
                        # Prefer adjective > noun > verb for derivational bases.
                        pos_pref = {"adj": 0, "noun": 1, "verb": 2}
                        best = min(non_adv, key=lambda p: (
                            pos_pref.get(self.lemmas[p].get("pos", ""), 99),
                            -self.lemmas[p].get("freq", 0),
                        ))
                        pids = [best]
            for pid in pids:
                if pid == cid:
                    # A lemma must never be its own derivational base
                    # (aquello resolves to the verb aquellar itself).
                    continue
                self.internal_children[pid].append((cid, affix))
                self.internal_parents[cid].append((pid, affix))
        for lid in self.lemmas:
            self.internal_degree[lid] = (
                len(self.internal_children.get(lid, [])) +
                len(self.internal_parents.get(lid, []))
            )

    def load_etymon_edges(self, edges):
        for e in edges:
            anc = e["ancestor"]
            lang = e.get("lang")
            mode = e.get("mode", "")
            lid = e["lemma_id"]
            if not _is_usable_ancestor(anc, lang, mode):
                continue
            self.etymon_index[anc].add(lid)
            self.ancestor_langs[lid][anc] = lang or ""
            self.lemma_ancestors[lid].add(anc)
            self.lemma_etymon_modes[lid].add(mode)

            # Only inherited-mode LATIN ancestors contribute root keys.
            # Old Spanish citations (osp "libro", "librar") are Spanish
            # words — deriving Latin supine keys from them ("libT") makes
            # liber "book" and liberare "free" collide and merges libro
            # with the free-family through E3.
            if mode in ("inherited", "inh", "inh+") and (lang or "").startswith("la"):
                rks = _latin_root_keys(anc)
                for rk in rks:
                    self.root_key_index[rk].add(lid)
                self.inh_root_keys[lid].update(rks)

    def load_etymtree_edges(self, edges):
        # Prose-tree ancestors never enter root_key_index.
        for e in edges:
            anc = e["ancestor"]
            lang = e.get("lang")
            lid = e["lemma_id"]
            if not _is_usable_ancestor(anc, lang, None):
                continue
            self.etymon_index[anc].add(lid)
            self.lemma_ancestors[lid].add(anc)

    def load_prose_edges(self, edges):
        """Load prose-parent links: (lemma_id, parent_word, kind).

        Resolution is lemma-only (exact word match first, then accent-folded)
        — the named parent must exist as a Spanish lemma.  Self-parents are
        dropped.  Edges are admitted at build time only when both endpoints
        pass the membership predicate.
        """
        for e in edges:
            lid = e["lemma_id"]
            pw = e["parent_word"]
            kind = e.get("kind", "from")
            pids_raw = self.word_index.get(fold(pw), [])
            exact = [p for p in pids_raw if self.lemmas[p]["word"] == pw]
            pids = exact or [p for p in pids_raw
                             if accent_strip(self.lemmas[p]["word"]) == accent_strip(pw)]
            for pid in pids:
                if pid == lid:
                    continue
                self.prose_parents[lid].append((pid, kind))


    def load_paradigm_buckets(self, lemma_forms):
        verbs = []
        for lid, forms in lemma_forms.items():
            rec = self.lemmas.get(lid)
            if rec and rec.get("pos") == "verb" and len(forms) >= 10:
                verbs.append({"id": lid, "forms": forms})
        raw = build_paradigm_buckets(verbs)
        ff = get_family_forming_buckets(raw, max_size=_MAX_BUCKET)
        self.family_forming_buckets = {k: set(v) for k, v in ff.items()}
        for rkey, lids in raw.items():
            for lid in lids:
                self.lemma_bucket[lid] = rkey
        for v in verbs:
            result = compute_paradigm_key(v["forms"])
            if result:
                P, residual = result
                self.lemma_prefix[v["id"]] = P

    def load_derived_links(self, links):
        self.derived_links = defaultdict(list, links)

    def load_related_links(self, links):
        self.related_links = defaultdict(list, links)

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    def _member_capable(self, lid: int) -> bool:
        rec = self.lemmas.get(lid)
        if rec is None:
            return False
        pos = rec.get("pos", "")
        if pos in _BOUND_POS:
            return False
        if fold(rec["word"]) in _FUNC_STOPLIST:
            return False

        # Redirect-gloss check MUST come before the forms check so that
        # synonym/alternative-form entries are always excluded, even when
        # a citation-form row has been added by another pipeline stage.
        gloss = rec.get("gloss", "") or ""
        if _re.match(
            r'^(synonym|alternative form|alternative spelling|obsolete form|'
            r'obsolete spelling|misspelling|superseded spelling|archaic form|'
            r'eye dialect|inflection) of\b', gloss, _re.IGNORECASE
        ):
            return False
        return True

    def _head_eligible(self, lid: int) -> bool:
        """Can this lemma head a family?  Content POS + forms required."""
        rec = self.lemmas.get(lid)
        if rec is None:
            return False
        if not self._member_capable(lid):
            return False
        if rec.get("pos", "") in _CLOSED_POS:
            return False
        if not rec.get("forms"):
            return False
        return True

    # ------------------------------------------------------------------
    # Hub detection
    # ------------------------------------------------------------------

    def _detect_hubs(self):
        self.hub_etymons.clear()
        self.hub_root_keys.clear()
        fanouts = [(anc, len(lids)) for anc, lids in self.etymon_index.items()]
        fanouts.sort(key=lambda x: -x[1])
        hubs = []
        for anc, sz in fanouts:
            if sz > _ETYMON_HUB:
                self.hub_etymons.add(anc)
                hubs.append((anc, sz))
        rk_fanouts = [(rk, len(lids)) for rk, lids in self.root_key_index.items()]
        rk_fanouts.sort(key=lambda x: -x[1])
        for rk, sz in rk_fanouts:
            if sz > _ROOT_KEY_HUB:
                self.hub_root_keys.add(rk)
        self._last_hubs = hubs[:20]
        return hubs

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, reject_log_path=None):
        hubs = self._detect_hubs()
        top_deg = sorted(self.internal_degree.items(), key=lambda x: -x[1])[:20]
        print(f"    Top INTERNAL-degree lemmas:")
        graph: dict[int, set[tuple[int, str, str]]] = defaultdict(set)
        A_cache: dict[int, set[str]] = {}
        A_derived_cache: dict[int, set[str]] = {}

        def get_A(lid):
            # Plain allomorphs — used by the E3 root-key gate.  The truncated
            # stem is NOT admitted here: E3's evidence is computed root keys
            # (supine-T keys + first4 overlap), which collide with truncated
            # stems (e.g. beleño ↔ belenismo via belen, carecer ↔ careo via
            # care).  Measured rescue precision was ~60%, below the bar.
            if lid not in A_cache:
                rec = self.lemmas[lid]
                A_cache[lid] = compute_allomorphs(rec["word"], rec.get("pos", ""), rec.get("forms", []))
            return A_cache[lid]

        def get_A_derived(lid):
            # Gated allomorphs (truncated stem admitted) — used by the E4/E4b
            # gates, whose evidence is the dictionary's own derived/related
            # word lists.  Measured rescue precision ~97%.
            if lid not in A_derived_cache:
                rec = self.lemmas[lid]
                A_derived_cache[lid] = _allomorphs_for_gates(rec["word"], rec.get("pos", ""), rec.get("forms", []))
            return A_derived_cache[lid]

        def _is_bare_component_of(lid: int, rid: int) -> bool:
            """True when either side's compound affix names the other side as
            a bare component (matar in mata + ojos, ojo in ojo + azul).
            Mirrors the J2 rule: a compound attaches to its last base via
            E1, and derived/related/prose evidence must not re-attach the
            non-base component — that is exactly how unrelated families
            bridge through compounds.
            """
            lwf = fold(self.lemmas[lid]["word"])
            rwf = fold(self.lemmas[rid]["word"])
            for src, other_fold in ((lid, rwf), (rid, lwf)):
                for _pid, affix in self.internal_parents.get(src, ()):
                    if not affix:
                        continue
                    if " " not in affix:
                        # single-token affix: bare component ("matar" in
                        # mata + ojos) or hyphenated prefix ("tele-" in
                        # tele- + tienda) — either names a component word
                        if fold(affix.strip("-")) == other_fold:
                            return True
                        continue
                    if affix.startswith("-") or affix.endswith("-"):
                        continue
                    for comp in affix.split(" + "):
                        if comp and fold(comp) == other_fold:
                            return True
            return False

        # Closed-class POS lemmas may hold at most ONE non-E5 edge (a
        # degree-1 leaf cannot bridge two families).  Edges are added in
        # precedence order (affix → paradigm → prose → root-key → derived),
        # so the first edge is always the best one.  E5 homograph edges are
        # exempt: merging a word with itself introduces no bridge.
        cap_deg: dict[int, int] = defaultdict(int)

        def _add_edge(lid: int, rid: int, rel: str, rlabel: str) -> bool:
            for end in (lid, rid):
                if self.lemmas[end].get("pos", "") in _CAP_POS and cap_deg[end] >= 1:
                    return False
            cap_deg[lid] += 1
            cap_deg[rid] += 1
            graph[lid].add((rid, rel, rlabel))
            graph[rid].add((lid, rel, rlabel))
            return True


        # ---- E1: affix edges ----
        # Compute E1 degree first.
        e1_deg: dict[int, int] = defaultdict(int)
        for lid in self.lemmas:
            # Stoplist words take no non-E5 edges at all — not even as
            # children (compounds whose last base is a function word stay
            # family-less rather than dragging the function word in).
            if fold(self.lemmas[lid]["word"]) in _FUNC_STOPLIST:
                continue
            child_eligible = self._member_capable(lid)
            for pid, affix in self.internal_parents.get(lid, []):
                if not self._member_capable(pid):
                    continue
                e1_deg[lid] += 1
                e1_deg[pid] += 1

        dropped_e1 = sorted([(lid, d) for lid, d in e1_deg.items() if d > _MAX_E1_DEGREE], key=lambda x: -x[1])
        if dropped_e1:
            print(f"    E1 cap ({_MAX_E1_DEGREE}): dropping {len(dropped_e1)} lemmas")
            for lid, deg in dropped_e1[:30]:
                r = self.lemmas.get(lid, {})
                print(f"      {deg:4d}  {r.get('word','?')} ({r.get('pos','?')})")

        for lid in self.lemmas:
            if fold(self.lemmas[lid]["word"]) in _FUNC_STOPLIST:
                continue
            child_eligible = self._member_capable(lid)
            if child_eligible and self.internal_degree.get(lid, 0) > _MAX_INTERNAL_DEGREE:
                continue
            if child_eligible and e1_deg.get(lid, 0) > _MAX_E1_DEGREE:
                continue
            # J2: for compounds with 2+ eligible parents, pick ONE edge target.
            # Only apply J2 when child is member-capable; other children
            # (e.g. multi-word phrases) accept all eligible parents.
            eligible_parents = [(pp, aa) for pp, aa in self.internal_parents.get(lid, [])
                                if self._member_capable(pp) and self.internal_degree.get(pp, 0) <= _MAX_INTERNAL_DEGREE
                                and e1_deg.get(pp, 0) <= _MAX_E1_DEGREE]
            selected_parent = None
            if len(eligible_parents) >= 2:
                verbs = [(pp, aa) for pp, aa in eligible_parents if self.lemmas[pp].get("pos") == "verb"]
                if verbs:
                    selected_parent = verbs[0][0]
                else:
                    selected_parent = max(eligible_parents, key=lambda x: (len(self.lemmas[x[0]]["word"]), self.lemmas[x[0]]["word"]))[0]
            for pid, affix in self.internal_parents.get(lid, []):
                if not self._member_capable(pid):
                    continue
                if self.internal_degree.get(pid, 0) > _MAX_INTERNAL_DEGREE:
                    continue
                if e1_deg.get(pid, 0) > _MAX_E1_DEGREE:
                    continue
                # J2: skip non-selected parents for compounds (only when child is eligible).
                if child_eligible and selected_parent is not None and pid != selected_parent:
                    continue
                mw = self.lemmas[pid]["word"]
                # Reject inflectional desinences masquerading as derivational affixes.
                if affix and affix.startswith("-"):
                    body = affix[1:]
                    if body in ("á", "é", "í", "ó", "ió", "a", "o",
                                "aba", "ara", "iera", "ase", "iese", "are", "iere"):
                        continue
                # Example: "estable" is not "estar + -able" — it's from Latin "stabilis".
                if affix and not affix.startswith("-") and not affix.endswith("-"):
                    child_ancs = self.lemma_ancestors.get(lid, set())
                    parent_ancs = self.lemma_ancestors.get(pid, set())
                    if child_ancs and parent_ancs:
                        child_rks = set()
                        for anc in child_ancs:
                            if _is_latin_ancestor(anc, None):
                                child_rks.update(_latin_root_keys(anc))
                        parent_rks = set()
                        for anc in parent_ancs:
                            if _is_latin_ancestor(anc, None):
                                parent_rks.update(_latin_root_keys(anc))
                        if child_rks and parent_rks and not (child_rks & parent_rks):
                            continue
                # Generate human label from affix string, never fabricate.

                if affix:
                    if " " in affix:
                        # Circumfix: "des- -ado" → "des- + base + -ado"
                        parts = affix.split()
                        prefix_part = next((p for p in parts if p.endswith("-")), "")
                        suffix_part = next((p for p in parts if p.startswith("-")), "")
                        rlabel = f"{prefix_part} + {mw} + {suffix_part}".replace(" +  + ", " + ")
                    elif affix.endswith("-"):
                        rlabel = f"{affix} + {mw}"
                    elif affix.startswith("-"):
                        rlabel = f"{mw} + {affix}"
                    elif affix.rstrip("-") in _SPANISH_PREFIXES:
                        # Bare component that is a known Spanish prefix: add hyphen.
                        rlabel = f"{affix}- + {mw}"
                    else:
                        rlabel = f"{affix} + {mw}" if len(affix) < len(mw) else f"{mw} + {affix}"
                else:
                    # Affix string missing from template — log and skip.
                    continue
                _add_edge(lid, pid, "affix", rlabel)

        # ---- E2: paradigm edges ----
        for lid in self.lemmas:
            lrec = self.lemmas[lid]
            if lrec.get("pos") != "verb":
                continue
            l_rkey = self.lemma_bucket.get(lid)
            if l_rkey is None:
                continue
            lP = self.lemma_prefix.get(lid, "")
            for rid in self.family_forming_buckets.get(l_rkey, ()):
                if rid <= lid:
                    continue
                rrec = self.lemmas[rid]
                if rrec.get("pos") != "verb":
                    continue
                rP = self.lemma_prefix.get(rid, "")
                if not lP or not rP:
                    continue
                # Condition 2: strictly longer prefix → compound.
                if len(lP) > len(rP):
                    cP, hP, cid, hid = lP, rP, lid, rid
                elif len(rP) > len(lP):
                    cP, hP, cid, hid = rP, lP, rid, lid
                else:
                    continue
                # Condition 3: cP must end with hP, or share Latin root key,
                # or compound is in head's derived list.
                if cP.endswith(hP):
                    pass
                else:
                    h_rks = set()
                    for anc in self.lemma_ancestors.get(hid, ()):
                        h_rks.update(_latin_root_keys(anc))
                    c_rks = set()
                    for anc in self.lemma_ancestors.get(cid, ()):
                        c_rks.update(_latin_root_keys(anc))
                    if h_rks & c_rks:
                        pass
                    else:
                        c_folded = fold(self.lemmas[cid]["word"])
                        if c_folded not in [fold(dw) for dw in self.derived_links.get(hid, [])]:
                            continue
                hw = self.lemmas[hid]["word"]
                _add_edge(cid, hid, "paradigm", rlabel)

        # ---- Prose edges: explicit parentage statements ----
        # "Deverbal from X", "Clipping of X", "Past participle of X" — the
        # dictionary states the parent explicitly, so these outrank computed
        # root-key matches but not affix templates.  Only kinds that assert
        # parentage explicitly are admitted; the bare "from X" and
        # "variant of X" gestures are dropped — they name cognates,
        # doublets, and foreign sources as often as real Spanish parents.
        _PROSE_LABELS = {
            "deverbal": "deverbal from",
            "participle": "past participle of",
            "clipping": "clipping of",
            "back-formation": "back-formation from",
            "abbreviation": "abbreviation of",
            "prothetic": "prothetic form of",
            "univerbation": "univerbation of",
            "from": "from",
            "variant": "variant of",
            "inflection": "inflection of",
        }
        _PROSE_KINDS = frozenset({
            "deverbal", "participle", "clipping", "back-formation",
            "abbreviation", "prothetic", "univerbation", "inflection",
        })
        # Bare "from X" / "variant of X" candidates are admitted ONLY when
        # the two citation forms pass the allomorph test: one accent-folded
        # form must start with a >=4-char allomorph of the other (after at
        # most one Spanish-prefix strip).  The sentence is the evidence of
        # connection; the stem overlap is the precision filter.
        # gracias/gracia share "graci"; querida/querer share "quer";
        # televisión/tele and a vague cognate almost never share a 4-char
        # stem, so those chains die.
        _gated_kinds = frozenset({"from", "variant"})
        _from_gate_cache: dict[int, set[str]] = {}

        def get_from_gate(lid):
            if lid not in _from_gate_cache:
                rec = self.lemmas[lid]
                _from_gate_cache[lid] = compute_allomorphs(
                    rec["word"], rec.get("pos", ""), rec.get("forms", []))
            return _from_gate_cache[lid]

        def _from_gate_ok(lid, pid):
            lf = accent_strip(self.lemmas[lid]["word"]).lower()
            pf = accent_strip(self.lemmas[pid]["word"]).lower()
            ls = strip_one_prefix(lf)
            ps = strip_one_prefix(pf)
            return (
                any(len(a) >= 4 and ps.startswith(a) for a in get_from_gate(lid))
                or any(len(a) >= 4 and ls.startswith(a) for a in get_from_gate(pid))
            )

        for lid in self.lemmas:
            if not self._member_capable(lid):
                continue
            for pid, kind in self.prose_parents.get(lid, []):
                if kind in _gated_kinds:
                    if not _from_gate_ok(lid, pid):
                        continue
                elif kind not in _PROSE_KINDS:
                    continue
                if not self._member_capable(pid):
                    continue
                if _is_bare_component_of(lid, pid):
                    continue
                mw = self.lemmas[pid]["word"]
                rlabel = f"{_PROSE_LABELS.get(kind, 'from')} {mw}"
                _add_edge(lid, pid, "prose", rlabel)

        # ---- E3: root-key edges ----
        for lid in self.lemmas:
            if lid in self.borrowed_lemmas:
                continue
            if not self._member_capable(lid):
                continue

            l_keys = set()
            anc_langs = self.ancestor_langs.get(lid, {})
            for anc in self.lemma_ancestors.get(lid, ()):
                if not (anc_langs.get(anc, "") or "").startswith("la"):
                    continue
                for rk in _latin_root_keys(anc):
                    if rk.endswith('T'):
                        l_keys.add(rk)
            if not l_keys:
                continue
            lA = get_A(lid)
            l_folded = accent_strip(self.lemmas[lid]["word"]).lower()
            l_stripped = strip_one_prefix(l_folded)
            for rk in l_keys:
                if rk in self.hub_root_keys:
                    continue
                if len(self.root_key_index.get(rk, ())) > _ROOT_KEY_HUB:
                    continue
                for rid in self.root_key_index.get(rk, ()):
                    if rid <= lid:
                        continue
                    if rid in self.borrowed_lemmas:
                        continue
                    if not self._member_capable(rid):
                        continue
                    rA = get_A(rid)
                    r_folded = accent_strip(self.lemmas[rid]["word"]).lower()
                    r_stripped = strip_one_prefix(r_folded)
                    ok = (any(len(a) >= 3 and r_stripped.startswith(a) for a in lA) or
                          any(len(a) >= 3 and l_stripped.startswith(a) for a in rA))
                    if ok:
                        # Require Latin ancestors with overlapping first4 prefixes.
                        # Computed supine-key alone is not enough — unrelated words
                        # can share a supine key (e.g. pono/pontus → ponT).
                        a_ancs = self.lemma_ancestors.get(lid, set())
                        b_ancs = self.lemma_ancestors.get(rid, set())
                        a_first4 = _latin_first4_set(a_ancs)
                        b_first4 = _latin_first4_set(b_ancs)
                        if not (a_first4 & b_first4):
                            continue
                        # Find best Latin ancestor label.
                        common = a_ancs & b_ancs
                        if common:
                            best = sorted(common, key=lambda x: -len(x))[0]
                            rlabel = f"inherited from Latin {best}"
                        else:
                            rlabel = f"same root as {self.lemmas[lid]['word']}"
                        _add_edge(lid, rid, "root-key", rlabel)

        # ---- E4: derived edges ----
        for lid in self.lemmas:
            if not self._member_capable(lid):
                continue
            lA = get_A_derived(lid)
            l_rks = set()
            for anc in self.lemma_ancestors.get(lid, ()):
                l_rks.update(_latin_root_keys(anc))
            for dw in self.derived_links.get(lid, []):
                for rid in self.word_index.get(fold(dw), []):
                    # No rid <= lid ordering condition: derived/related lists
                    # are per-lemma and asymmetric — every listed pair must
                    # be visited regardless of id order.
                    if rid == lid:
                        continue
                    if not self._member_capable(rid):
                        continue
                    if _is_bare_component_of(lid, rid):
                        continue
                    r_folded = accent_strip(self.lemmas[rid]["word"]).lower()
                    r_stripped = strip_one_prefix(r_folded)
                    if any(len(a) >= 3 and r_stripped.startswith(a) for a in lA):
                        # Gate: require shared Latin root keys.  Derived links
                        # (Wiktionary "derived" section) often mix in antonyms,
                        # synonyms, and compounds that bridge unrelated Latin
                        # roots.  Without root-key overlap the connection is too
                        # weak — the words should already share E1 or E3 edges.
                        r_rks = set()
                        for anc in self.lemma_ancestors.get(rid, ()):
                            r_rks.update(_latin_root_keys(anc))
                        if not (l_rks and r_rks and (l_rks & r_rks)):
                            continue
                        _add_edge(lid, rid, "derived", f"related to {self.lemmas[lid]['word']}")

        # ---- E4b: related edges ----
        # Admitted when:
        #   (a) the pair is an accent variant of one word (aun/aún, gombo/gombó);
        #   (b) one citation form contains the other AND the target starts
        #       with a source stem — the containment + allomorph pair that
        #       stops mentir ↔ mente ("mente" starts with "ment" but neither
        #       citation contains the other) and bien ↔ bienhechor ("bien"
        #       is stripped as a Spanish prefix before the allomorph test);
        #   (c) one is an inflectional variant of the other (gracias/gracia);
        #   (d) the two share a Latin root key — exact non-supine overlap of
        #       any-mode ancestor keys, or first3 overlap of inherited-mode
        #       keys.  Branch (d) requires disjoint ancestor sets: a pair
        #       sharing the SAME exact etymon (ir/ser both citing esse) is a
        #       suppletion or synonym chain, not a derivation.  It is also
        #       disabled when one citation contains the other, so a compound
        #       component cannot re-enter through root keys.
        e4b_cache: dict[int, tuple] = {}

        def get_e4b(lid):
            if lid not in e4b_cache:
                l_keys = {rk for anc in self.lemma_ancestors.get(lid, ())
                          for rk in _latin_root_keys(anc)}
                l_nonsup = {k for k in l_keys if not k.endswith("T")}
                l_inh = {k[:3] for k in self.inh_root_keys.get(lid, ())}
                e4b_cache[lid] = (l_nonsup, l_inh)
            return e4b_cache[lid]

        for lid in self.lemmas:
            if not self._member_capable(lid):
                continue
            lw = self.lemmas[lid]["word"]
            lwf = fold(lw)
            lA = get_A_derived(lid)
            l_nonsup, l_inh = get_e4b(lid)
            for rw in self.related_links.get(lid, []):
                for rid in self.word_index.get(fold(rw), []):
                    if rid == lid:
                        continue
                    if not self._member_capable(rid):
                        continue
                    if _is_bare_component_of(lid, rid):
                        continue
                    rww = self.lemmas[rid]["word"]
                    rwf = fold(rww)
                    contained = lwf in rwf or rwf in lwf
                    # (a) accent variant
                    admitted = lwf == rwf
                    child_side = None
                    # (b) substring containment AND allomorph prefix
                    if not admitted and contained:
                        r_stripped = strip_one_prefix(accent_strip(rww).lower())
                        admitted = any(len(a) >= 3 and r_stripped.startswith(a) for a in lA)
                        child_side = rid if admitted else None
                    # (c) strict inflectional pair (plural/gender variant)
                    if not admitted:
                        admitted = _is_inflectional_pair(lwf, rwf)
                        child_side = lid if admitted else None
                    # (d) shared Latin root key — disjoint ancestors, no
                    # citation containment, exact non-supine overlap only.
                    # Prefix-level key matches are rejected: sentire/sedentare
                    # (sentir/sentar) collide at first3 and first4, so any
                    # looser test re-bridges unrelated roots.
                    if not admitted and not contained:
                        if not (self.lemma_ancestors.get(lid, set()) & self.lemma_ancestors.get(rid, set())):
                            r_nonsup, _r_inh = get_e4b(rid)
                            if l_nonsup and r_nonsup and (l_nonsup & r_nonsup):
                                admitted = True
                    if admitted:
                        if child_side is not None:
                            pass
                        _add_edge(lid, rid, "derived", f"related to {self.lemmas[lid]['word']}")
        # Same lexeme with different POS hats must land in one family.  The
        # POS exclusion does NOT apply here — merging a word with itself can
        # never introduce a bridge.  Gate: overlapping ancestor sets; or one
        # entry has no etymology of its own; or both entries have only
        # internal (E1) derivation and share a parent.  Never merge on
        # spelling alone — distinct etyma (haz < fascis vs haz < facies)
        # stay apart.
        word_groups: dict[str, list[int]] = defaultdict(list)
        for lid in self.lemmas:
            # Exclude names (proper nouns) from E5 — they are not the same
            # lexeme as content-word homographs.
            if self.lemmas[lid].get("pos") != "name":
                word_groups[self.lemmas[lid]["word"]].append(lid)
        for lids in word_groups.values():
            if len(lids) < 2:
                continue
            for i in range(len(lids)):
                a = lids[i]
                a_ancs = self.lemma_ancestors.get(a, set())
                a_e1 = {pid for pid, _ in self.internal_parents.get(a, [])}
                for j in range(i + 1, len(lids)):
                    b = lids[j]
                    b_ancs = self.lemma_ancestors.get(b, set())
                    b_e1 = {pid for pid, _ in self.internal_parents.get(b, [])}
                    if a_ancs and b_ancs:
                        # Both have ancestry: require overlap.
                        if not (a_ancs & b_ancs):
                            continue
                    elif a_ancs or b_ancs:
                        # Exactly one has ancestry: merge only when the other
                        # has no etymology data of its own at all.
                        if (a_ancs and b_e1) or (b_ancs and a_e1):
                            continue
                    elif a_e1 and b_e1:
                        # Both derived internally: merge only on a shared
                        # parent (demás adj/adv/pron all cite más; adiós
                        # intj/noun both cite Dios).
                        if not (a_e1 & b_e1):
                            continue
                    elif a_e1 or b_e1:
                        pass
                    else:
                        # Neither has any etymology data — can't judge, skip.
                        continue
                    # Label from the member's own POS perspective.
                    a_pos = self.lemmas[a].get("pos", "?")
                    b_pos = self.lemmas[b].get("pos", "?")
                    graph[a].add((b, "homograph", f"{a_pos} use of {self.lemmas[a]['word']}"))
                    graph[b].add((a, "homograph", f"{b_pos} use of {self.lemmas[a]['word']}"))
        print(f"    Graph built: {sum(len(v) for v in graph.values()) // 2} edges")
        self.graph = graph

        # ---- Connected components ----


        visited: set[int] = set()
        components: list[set[int]] = []
        for lid in self.lemmas:
            if lid in visited:
                continue
            comp: set[int] = set()
            stack = [lid]
            while stack:
                cur = stack.pop()
                if cur in comp:
                    continue
                comp.add(cur)
                visited.add(cur)
                for other, rel, rlabel in graph.get(cur, ()):
                    if other not in comp:
                        stack.append(other)
            if comp:
                components.append(comp)
        # ---- Assign families ----
        self.families.clear()
        self.family_of.clear()
        fid_counter = 1

        for comp in components:
            if not comp:
                continue
            # Select head: the member that is a transitive ancestor of the
            # most other members in the directed graph of E1 + prose parent
            # edges (the word everything else was built from).  Tie-break:
            # frequency desc, shortest citation form, then word asc.
            eligible = [lid for lid in comp if self._head_eligible(lid)]
            if not eligible:
                continue

            # Directed parent->child edges inside the component: E1 (via
            # internal_parents, only when the affix edge actually formed)
            # and prose (via prose_parents, only when the prose edge formed).
            par_child: dict[int, set[int]] = defaultdict(set)
            for lid in comp:
                for pid, _affix in self.internal_parents.get(lid, ()):
                    if pid in comp and any(o == pid for o, _r, _l in graph.get(lid, ()) if _r == "affix"):
                        par_child[pid].add(lid)
                for pid, _kind in self.prose_parents.get(lid, ()):
                    if pid in comp and any(o == pid for o, _r, _l in graph.get(lid, ()) if _r == "prose"):
                        par_child[pid].add(lid)

            desc_count: dict[int, int] = {}
            for root in comp:
                seen = set()
                stack = [root]
                while stack:
                    cur = stack.pop()
                    for ch in par_child.get(cur, ()):
                        if ch not in seen:
                            seen.add(ch)
                            stack.append(ch)
                desc_count[root] = len(seen)

            def _head_key(lid):
                rec = self.lemmas[lid]
                return (
                    -desc_count.get(lid, 0),
                    -rec.get("freq", 0),
                    len(rec["word"]),
                    rec["word"],
                )
            head_id = min(eligible, key=_head_key)
            head_word = self.lemmas[head_id]["word"]

            # BFS labels: first compute depths, then each member picks the best
            # edge from among neighbors at strictly smaller depth.
            _REL_ORDER = {"affix": 0, "paradigm": 1, "prose": 2, "root-key": 3, "derived": 4, "homograph": 5}
            members: dict[int, dict] = {head_id: {"relation": "root", "relation_label": "root"}}
            depth: dict[int, int] = {head_id: 0}
            queue = [head_id]
            visited_bfs = {head_id}
            while queue:
                cur = queue.pop(0)
                for other, rel, rlabel in graph.get(cur, ()):
                    if other not in comp:
                        continue
                    if other not in visited_bfs:
                        visited_bfs.add(other)
                        queue.append(other)
                        depth[other] = depth[cur] + 1

            for mid in comp:
                if mid == head_id:
                    continue
                # Collect candidate edges from neighbors at strictly smaller depth.
                candidates = []
                for other, rel, rlabel in graph.get(mid, ()):
                    if other not in comp:
                        continue
                    d = depth.get(other)
                    if d is not None and d < depth[mid]:
                        candidates.append((other, rel, rlabel, d))
                if candidates:
                    # Best precedence, then closest to root, then alphabetic.
                    best = min(candidates, key=lambda x: (
                        _REL_ORDER.get(x[1], 99),
                        x[3],
                        self.lemmas[x[0]]["word"],
                    ))
                    parent, rel, rlabel = best[0], best[1], best[2]
                    mw = self.lemmas[mid]["word"]
                    pw = self.lemmas[parent]["word"]
                    # Generate label from edge type.
                    if rel == "affix":
                        if mw in rlabel:
                            # The edge's rlabel names the member as the
                            # derivational base — the member is the base of
                            # the word on the other side of this edge.
                            label = f"base of {pw}"
                        else:
                            label = rlabel

                    elif rel == "paradigm":
                        label = f"same paradigm as {head_word}"
                    elif rel == "root-key":
                        # Use member's own LATIN ancestor (lang starts with "la").
                        # Fall back to Old Spanish if no Latin ancestor exists.
                        own_anc = None
                        own_anc_osp = None
                        comp_words = {self.lemmas[l]["word"] for l in comp}
                        for anc in sorted(self.lemma_ancestors.get(mid, set()), key=lambda x: -len(x)):
                            if len(anc) < 4 or anc in comp_words:
                                continue
                            lang = self.ancestor_langs.get(mid, {}).get(anc, "")
                            if lang.startswith("la"):
                                own_anc = anc
                                break
                            elif lang in ("osp",) and own_anc_osp is None:
                                own_anc_osp = anc
                        if own_anc:
                            label = f"inherited from Latin {own_anc}"
                        elif own_anc_osp:
                            label = f"inherited from Old Spanish {own_anc_osp}"
                        else:
                            label = f"same root as {head_word}"
                    elif rel == "derived":
                        label = f"related to {head_word}"
                    elif rel == "prose":
                        # Explicit parentage statement — use it verbatim
                        # ("deverbal from probar", "clipping of automóvil").
                        label = rlabel
                    elif rel == "homograph":
                        # Use the edge's own label (e.g. "noun use of rápido")
                        label = rlabel
                    else:
                        label = rel
                    members[mid] = {"relation": rel, "relation_label": label, "_parent": pw}
                else:
                    members[mid] = {"relation": "root", "relation_label": "root"}

            # Assert labels: reject empty, machine codes, and self-referential
            # labels, and guard against the doubled-substring corruption that
            # member-word replacement used to cause ("same paradigm as
            # escarescarmentar" = prefix "escar" + head "escarmentar").
            for mid in comp:
                if mid == head_id:
                    continue
                info = members.get(mid, {})
                if not info:
                    info = {}
                    members[mid] = info
                label = info.get("relation_label", "")
                relation = info.get("relation", "")
                mw = self.lemmas[mid]["word"]
                if not label or label in ("affix", "paradigm", "root-key", "derived", "homograph", "root"):
                    info["relation_label"] = f"related to {head_word}"
                    relation = "derived"
                    label = info["relation_label"]
                # Build-time label integrity.  Machine-generated labels
                # (paradigm/derived/root-key/homograph) name the family
                # head as a full token — the head word must never appear
                # spliced inside another token ("tele- + teleentender",
                # "día entenderdo + -ado").  Affix labels must name their
                if relation in ("paradigm", "derived"):
                    for tok in _re.split(r"[\s+]+", label):
                        if tok and tok != head_word and head_word in tok:
                            raise AssertionError(
                                f"head word spliced into label for {mw!r}: {label!r} "
                                f"(token {tok!r}, head {head_word!r})")
                if relation == "affix":
                    parts = label.split(" + ")
                    pw2 = info.get("_parent", "")
                    if label != f"base of {pw2}" and pw2 not in parts:
                        raise AssertionError(
                            f"affix label for {mw!r} does not name its parent {pw2!r}: {label!r}")
                if label.startswith("inherited from Latin ") and label[len("inherited from Latin "):] in {self.lemmas[l]["word"] for l in comp}:
                    info["relation_label"] = f"same root as {head_word}"
                    relation = "root-key"
                # Build-time assertions: paradigm and derived labels must
                # name the family head, nothing else.
                if relation == "paradigm" and info["relation_label"] != f"same paradigm as {head_word}":
                    raise AssertionError(
                        f"corrupted paradigm label for {mw!r}: {info['relation_label']!r} "
                        f"(expected 'same paradigm as {head_word}')")
                if relation == "derived" and info["relation_label"] != f"related to {head_word}":
                    raise AssertionError(
                        f"corrupted derived label for {mw!r}: {info['relation_label']!r} "
                        f"(expected 'related to {head_word}')")
            self.families[fid_counter] = {"head_id": head_id, "members": members}
            for mid in members:
                self.family_of[mid] = fid_counter
            fid_counter += 1

        # Singletons.
        for lid in self.lemmas:
            if lid not in self.family_of:  # J3: all lemmas get families
                self.families[fid_counter] = {
                    "head_id": lid,
                    "members": {lid: {"relation": "root", "relation_label": "root"}},
                }
                self.family_of[lid] = fid_counter
                fid_counter += 1

        return self.families

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_family_members(self, family_id):
        return self.families.get(family_id, {}).get("members", {})

    def get_family_id(self, lemma_id):
        return self.family_of.get(lemma_id)
