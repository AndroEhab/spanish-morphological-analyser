"""Family construction — connected components of a strictly-gated admission graph.

Consolidated rewrite. Edge rules: E1 (affix), E2 (paradigm), E3 (root-key), E4 (derived).
Families = connected components. Ancestors only from structured templates, never prose trees.
"""

from __future__ import annotations

from collections import defaultdict
import re as _re

from pipeline.normalize import fold, accent_strip
from pipeline.paradigm import compute_allomorphs, strip_one_prefix, get_family_forming_buckets, compute_paradigm_key, build_paradigm_buckets

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

_BANNED_LANGS = frozenset({
    "ine-pro", "itc-pro", "gem-pro", "cel-pro", "grk-pro",
    "sla-pro", "bat-pro", "ine", "qfa-sub", "sem-pro", "afa-pro",
})

_JUNK_ANCESTOR_RE = _re.compile(r'[()<>,]|\s|[0-9]')
_LATIN_VERB_RE = _re.compile(r'(re|o|io|are|ere|ire|ari|iri)$')
_LATIN_NOMINAL_RE = _re.compile(
    r'(ndus|nda|ndum|ndo|tura|tus|ta|tum|tor|torem|tio|tionem|ticius|tivus|tilis|bilis|men|mentum|trix)$')

_CLOSED_POS = frozenset({
    "conj", "pron", "prep", "det", "article", "particle",
    "num", "intj", "suffix", "prefix", "interfix", "infix",
    "name", "phrase", "proverb", "prep_phrase", "adv_phrase",
    "character", "punct", "symbol",
})

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

        self.allomorphs_cache: dict[int, set[str]] = {}

        self.families: dict[int, dict] = {}
        self.family_of: dict[int, int] = {}
        self._last_hubs: list[tuple[str, int]] = []

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
            # Only accept word-index matches where the lemma's word is the
            # same as the parent word after accent-stripping (exact match
            # excluding diacritics).  This prevents collisions like "sola"
            # (feminine form) matching "Sola" (proper name).
            pids = [p for p in pids_raw
                    if self.lemmas[p]["word"] == pw
                    or accent_strip(self.lemmas[p]["word"]) == accent_strip(pw)]
            if not pids:
                # Resolve component through form table when it is not a lemma
                # (e.g. feminine form cited as base for -mente adverb).
                form_pids = self.form_to_lemmas.get(fold(pw), set())
                if len(form_pids) == 1:
                    pids = list(form_pids)
                elif len(form_pids) > 1:
                    # Ambiguous: prefer candidates with non-adv POS (the
                    # base of an adverb is almost never an adverb itself).
                    non_adv = [p for p in form_pids if self.lemmas[p].get("pos") != "adv"]
                    if non_adv:
                        # Prefer adjective > noun > verb for derivational bases.
                        pos_pref = {"adj": 0, "noun": 1, "verb": 2}
                        best = min(non_adv, key=lambda p: (
                            pos_pref.get(self.lemmas[p].get("pos", ""), 99),
                            -self.lemmas[p].get("freq", 0),
                        ))
                        pids = [best]
            for pid in pids:
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
            if mode == "borrowed":
                self.borrowed_lemmas.add(lid)
            # Only inherited-mode ancestors contribute root keys (inh/inh+/inherited).
            if mode in ("inherited", "inh", "inh+") and _is_latin_ancestor(anc, lang):
                for rk in _latin_root_keys(anc):
                    self.root_key_index[rk].add(lid)

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

    def _eligible(self, lid: int) -> bool:
        rec = self.lemmas.get(lid)
        if rec is None:
            return False
        pos = rec.get("pos", "")
        if pos in _CLOSED_POS:
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

        def get_A(lid):
            if lid not in A_cache:
                rec = self.lemmas[lid]
                A_cache[lid] = compute_allomorphs(rec["word"], rec.get("pos", ""), rec.get("forms", []))
            return A_cache[lid]

        # ---- E1: affix edges ----
        # Compute E1 degree first.
        e1_deg: dict[int, int] = defaultdict(int)
        for lid in self.lemmas:
            child_eligible = self._eligible(lid)
            for pid, affix in self.internal_parents.get(lid, []):
                if not self._eligible(pid):
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
            child_eligible = self._eligible(lid)
            if child_eligible and self.internal_degree.get(lid, 0) > _MAX_INTERNAL_DEGREE:
                continue
            if child_eligible and e1_deg.get(lid, 0) > _MAX_E1_DEGREE:
                continue
            # J2: for compounds with 2+ eligible parents, pick ONE edge target.
            # Only apply J2 when child is eligible; ineligible children
            # (e.g. adverbs without forms) accept all eligible parents.
            eligible_parents = [(pp, aa) for pp, aa in self.internal_parents.get(lid, [])
                                if self._eligible(pp) and self.internal_degree.get(pp, 0) <= _MAX_INTERNAL_DEGREE
                                and e1_deg.get(pp, 0) <= _MAX_E1_DEGREE]
            selected_parent = None
            if len(eligible_parents) >= 2:
                verbs = [(pp, aa) for pp, aa in eligible_parents if self.lemmas[pp].get("pos") == "verb"]
                if verbs:
                    selected_parent = verbs[0][0]
                else:
                    selected_parent = max(eligible_parents, key=lambda x: (len(self.lemmas[x[0]]["word"]), self.lemmas[x[0]]["word"]))[0]
            for pid, affix in self.internal_parents.get(lid, []):
                if not self._eligible(pid):
                    continue
                if self.internal_degree.get(pid, 0) > _MAX_INTERNAL_DEGREE:
                    continue
                if e1_deg.get(pid, 0) > _MAX_E1_DEGREE:
                    continue
                # J2: skip non-selected parents for compounds (only when child is eligible).
                if child_eligible and selected_parent is not None and pid != selected_parent:
                    continue
                mw = self.lemmas[pid]["word"]
                lw = self.lemmas[lid]["word"]
                # If the child has independent Latin provenance (root keys not
                # overlapping the parent's), skip this Spanish-internal edge.
                # Only applies to lexical-base compounds (bare-word affixes);
                # genuine prefixes/suffixes are exempt.
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
                # Reject inflectional desinences masquerading as derivational affixes.
                # -á, -é, -í, -ó, -ió are verb endings, never derivational suffixes.
                if affix and affix.startswith("-"):
                    body = affix[1:]
                    if body in ("á", "é", "í", "ó", "ió", "a", "e", "o",
                                "aba", "ía", "ara", "iera", "ase", "iese", "are", "iere"):
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
                graph[lid].add((pid, "affix", rlabel))
                graph[pid].add((lid, "affix", rlabel))

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
                rlabel = f"same paradigm as {hw}"
                graph[cid].add((hid, "paradigm", rlabel))
                graph[hid].add((cid, "paradigm", rlabel))

        # ---- E3: root-key edges ----
        for lid in self.lemmas:
            if lid in self.borrowed_lemmas:
                continue
            if not self._eligible(lid):
                continue
            l_keys = set()
            for anc in self.lemma_ancestors.get(lid, ()):
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
                    if not self._eligible(rid):
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
                        graph[lid].add((rid, "root-key", rlabel))
                        graph[rid].add((lid, "root-key", rlabel))

        # ---- E4: derived edges ----
        for lid in self.lemmas:
            if not self._eligible(lid):
                continue
            lA = get_A(lid)
            l_rks = set()
            for anc in self.lemma_ancestors.get(lid, ()):
                l_rks.update(_latin_root_keys(anc))
            for dw in self.derived_links.get(lid, []):
                for rid in self.word_index.get(fold(dw), []):
                    if rid <= lid:
                        continue
                    if not self._eligible(rid):
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
                        graph[lid].add((rid, "derived", f"related to {self.lemmas[lid]['word']}"))
                        graph[rid].add((lid, "derived", f"related to {self.lemmas[lid]['word']}"))

        # ---- E4b: related edges (substring-gated) ----
        for lid in self.lemmas:
            if not self._eligible(lid):
                continue
            lw = self.lemmas[lid]["word"].lower()
            lA = get_A(lid)
            for rw in self.related_links.get(lid, []):
                for rid in self.word_index.get(fold(rw), []):
                    if rid <= lid:
                        continue
                    if not self._eligible(rid):
                        continue
                    rww = self.lemmas[rid]["word"].lower()
                    # Only create edge if one word contains the other as substring.
                    if lw not in rww and rww not in lw:
                        continue
                    r_folded = accent_strip(self.lemmas[rid]["word"]).lower()
                    r_stripped = strip_one_prefix(r_folded)
                    if any(len(a) >= 3 and r_stripped.startswith(a) for a in lA):
                        graph[lid].add((rid, "derived", f"related to {self.lemmas[lid]['word']}"))
                        graph[rid].add((lid, "derived", f"related to {self.lemmas[lid]['word']}"))

        # ---- E5: POS homograph edges ----
        # Same lexeme with different POS hats (e.g. rápido adj/adv/noun) must
        # land in the same family when they share etymology.  Gate: overlapping
        # ancestor sets, or one entry has no etymology of its own.  Never merge
        # on spelling alone — distinct etyma (haz < fascis vs haz < facies)
        # stay apart.  Both endpoints must be eligible (names, interjections
        # and other closed-class lemmas are excluded).
        word_groups: dict[str, list[int]] = defaultdict(list)
        for lid in self.lemmas:
            # Exclude names (proper nouns) from E5 — they are not the same
            # lexeme as content-word homographs.  Adverbs and interjections
            # that happen to lack forms ARE included; their etymology gate
            # is handled below.
            if self.lemmas[lid].get("pos") != "name":
                 word_groups[self.lemmas[lid]["word"]].append(lid)
        for lids in word_groups.values():
            if len(lids) < 2:
                continue
            for i in range(len(lids)):
                a = lids[i]
                a_ancs = self.lemma_ancestors.get(a, set())
                a_has_e1 = bool(self.internal_parents.get(a))
                for j in range(i + 1, len(lids)):
                    b = lids[j]
                    b_ancs = self.lemma_ancestors.get(b, set())
                    b_has_e1 = bool(self.internal_parents.get(b))
                    # Both have structured etymology (ancestors or E1).  
                    # If ancestors overlap → same lexeme.  If not → distinct.
                    if a_ancs and b_ancs:
                        if not (a_ancs & b_ancs):
                            continue
                    elif (a_ancs or a_has_e1) and (b_ancs or b_has_e1):
                        # Both have etymology data of some kind but ancestors
                        # don't overlap (and neither is empty-etymology).
                        continue
                    elif not a_ancs and not a_has_e1 and not b_ancs and not b_has_e1:
                        # Neither has any etymology data — can't judge, skip.
                        continue
                    # Label from the member's own POS perspective.
                    # e.g. the noun entry reads "noun use of the adjective rápido".
                    a_pos = self.lemmas[a].get("pos", "?")
                    b_pos = self.lemmas[b].get("pos", "?")
                    graph[a].add((b, "homograph", f"{a_pos} use of {self.lemmas[a]['word']}"))
                    graph[b].add((a, "homograph", f"{b_pos} use of {self.lemmas[a]['word']}"))

        print(f"    Graph built: {sum(len(v) for v in graph.values()) // 2} edges")

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
            # Select head.
            eligible = [lid for lid in comp if self._eligible(lid)]
            if not eligible:
                continue

            def _head_key(lid):
                rec = self.lemmas[lid]
                pos_order = {"verb": 0, "adj": 1, "noun": 2, "adv": 3}
                n_e1 = sum(1 for o, r, l in graph.get(lid, ()) if r == "affix")
                # Prefer derivational roots: members with no E1 parent (i.e.
                # nothing in the family derives them) before applying POS order.
                has_e1_parent = any(pid in comp for pid, _ in self.internal_parents.get(lid, ()))
                return (
                    has_e1_parent,          # False (0) = preferred (no parent)
                    pos_order.get(rec.get("pos", ""), 99),
                    -rec.get("freq", 0),
                    len(rec["word"]),
                    -n_e1,
                    rec["word"],
                )
            head_id = min(eligible, key=_head_key)
            head_word = self.lemmas[head_id]["word"]

            # BFS labels: first compute depths, then each member picks the best
            # edge from among neighbors at strictly smaller depth.
            _REL_ORDER = {"affix": 0, "paradigm": 1, "root-key": 2, "derived": 3, "homograph": 4}
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
                        label = rlabel
                        if mw in label and mw != pw:
                            parts = label.split(" + ", 1)
                            if len(parts) == 2:
                                left, right = parts
                                if mw in left:
                                    label = left.replace(mw, pw) + " + " + right
                                else:
                                    label = left + " + " + right.replace(mw, pw)
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
                    elif rel == "homograph":
                        # Use the edge's own label (e.g. "noun use of rápido")
                        # rather than a generic self-referential one.
                        label = rlabel
                    else:
                        label = rel
                    members[mid] = {"relation": rel, "relation_label": label}
                else:
                    members[mid] = {"relation": "root", "relation_label": "root"}

            # Assert labels: reject empty, machine codes, and self-referential labels.
            for mid in comp:
                if mid == head_id:
                    continue
                info = members.get(mid, {})
                if not info:
                    info = {}
                    members[mid] = info
                label = info.get("relation_label", "")
                mw = self.lemmas[mid]["word"]
                if not label or label in ("affix", "paradigm", "root-key", "derived", "homograph", "root"):
                    info["relation_label"] = f"related to {head_word}"
                if mw in label and rel != "homograph":
                    info["relation_label"] = label.replace(mw, head_word)
                if label.startswith("inherited from Latin ") and label[len("inherited from Latin "):] in {self.lemmas[l]["word"] for l in comp}:
                    info["relation_label"] = f"same root as {head_word}"
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
