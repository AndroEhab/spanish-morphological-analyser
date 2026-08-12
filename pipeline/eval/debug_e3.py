#!/usr/bin/env python3
"""Quick E3 debugger — added to trace.py via import."""

import json, sys
from pathlib import Path
from collections import defaultdict

from pipeline.normalize import fold, accent_strip
from pipeline.etymology import parse_templates
from pipeline.paradigm import compute_allomorphs, strip_one_prefix, build_paradigm_buckets, compute_paradigm_key
from pipeline.family import FamilyBuilder, _latin_root_keys, _is_usable_ancestor, _is_latin_ancestor, _allomorphs_for_gates

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def load_data():
    lemma_records = {}
    lemma_forms_raw = {}
    with open(DATA_DIR / "lemmas.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            rec = json.loads(line)
            lemma_records[rec["id"]] = rec
            lemma_forms_raw[rec["id"]] = rec.get("forms", [])
    return lemma_records, lemma_forms_raw

def build_edges(lemma_records, lemma_forms_raw):
    internal_edges, etymon_edges, etymtree_edges = [], [], []
    for lid, rec in lemma_records.items():
        parsed = parse_templates(rec["word"], rec.get("etymology_templates", "[]"), rec.get("etymology_text", ""))
        for pw, affix in parsed["internal"]:
            internal_edges.append({"lemma_id": lid, "parent_word": pw, "affix": affix})
        for anc, lang, mode, src in parsed["etymons"]:
            etymon_edges.append({"lemma_id": lid, "ancestor": anc, "lang": lang, "mode": mode, "source_word": src})
        for anc, lang in parsed["etymtree_ancestors"]:
            etymtree_edges.append({"lemma_id": lid, "ancestor": anc, "lang": lang})

    builder = FamilyBuilder()
    builder.load_lemmas(list(lemma_records.values()))
    builder.load_internal_edges(internal_edges)
    builder.load_etymon_edges(etymon_edges)
    builder.load_etymtree_edges(etymtree_edges)
    builder.load_paradigm_buckets(lemma_forms_raw)
    derived_links = {}
    for lid, rec in lemma_records.items():
        dr = rec.get("derived_related", [])
        if dr: derived_links[lid] = dr
    builder.load_derived_links(derived_links)
    return builder

def find_id(lemma_records, word, pos=None):
    folded = fold(word)
    for lid, rec in lemma_records.items():
        if fold(rec["word"]) == folded:
            if pos is None or rec.get("pos") == pos:
                return lid
    return None

def debug_e3(w1, w2):
    lemma_records, lemma_forms_raw = load_data()
    builder = build_edges(lemma_records, lemma_forms_raw)
    
    for w in (w1, w2):
        ids = [lid for lid, rec in lemma_records.items() if fold(rec["word"]) == fold(w)]
        print(f"\n=== {w} ({len(ids)} entries) ===")
        for lid in ids:
            rec = lemma_records[lid]
            print(f"  id={lid} pos={rec['pos']} etym_no={rec.get('etym_no',0)}")
            print(f"  eligible: {builder._eligible(lid)}")
            if not builder._eligible(lid):
                print(f"    forms={bool(rec.get('forms'))}, gloss={rec.get('gloss','')[:50]}")
                pos = rec.get('pos','')
                in_closed = pos in {'conj','pron','prep','det','article','particle','num','intj','suffix','prefix','interfix','infix','name','phrase','proverb','prep_phrase','adv_phrase','character','punct','symbol'}
                in_stoplist = fold(rec['word']) in {'que','no','se','lo','la','le','me','te','nos','os','y','o','a','de','en','por','para','con','sin','al','del','es','si','ya','mas','muy','tan'}
                print(f'    in_closed_pos={in_closed}, in_stoplist={in_stoplist}')
            
            # Ancestor records
            print(f"  ancestors ({len(builder.lemma_ancestors.get(lid, set()))}):")
            for anc in sorted(builder.lemma_ancestors.get(lid, set())):
                rk = _latin_root_keys(anc)
                t_keys = [k for k in rk if k.endswith('T')]
                print(f"    {anc} -> root_keys={rk} supine={t_keys}")
            
            # Root keys (supine only)
            all_keys = set()
            for anc in builder.lemma_ancestors.get(lid, set()):
                for rk in _latin_root_keys(anc):
                    if rk.endswith('T'):
                        all_keys.add(rk)
            print(f"  supine keys: {sorted(all_keys)}")
            
            # Allomorphs (E4 gated set incl. truncated stem; E3 uses the plain set)
            allos = _allomorphs_for_gates(rec["word"], rec.get("pos",""), rec.get("forms",[]))
            a3 = sorted([a for a in allos if len(a) >= 3])
            print(f"  allomorphs (len>=3): {a3[:20]}{'...' if len(a3) > 20 else ''}")
    
    # Find shared keys and check fan-out
    id1 = find_id(lemma_records, w1)
    id2 = find_id(lemma_records, w2)
    if id1 and id2:
        keys1 = set()
        for anc in builder.lemma_ancestors.get(id1, set()):
            for rk in _latin_root_keys(anc):
                if rk.endswith('T'): keys1.add(rk)
        keys2 = set()
        for anc in builder.lemma_ancestors.get(id2, set()):
            for rk in _latin_root_keys(anc):
                if rk.endswith('T'): keys2.add(rk)
        shared = keys1 & keys2
        print(f"\n=== Shared supine keys: {sorted(shared)} ===")
        for rk in sorted(shared):
            fanout = len(builder.root_key_index.get(rk, set()))
            is_hub = rk in builder.hub_root_keys
            over_cap = fanout > 400
            print(f"  {rk}: fanout={fanout}, is_hub={is_hub}, over_400={over_cap}")
            if is_hub or over_cap:
                print(f"    WOULD BE SKIPPED by E3 loop!")
        
        # Allomorph test — E3 uses the PLAIN allomorph set; the truncated
        # stem is only admitted by the E4/E4b (derived/related) gates.
        rec1 = lemma_records[id1]
        rec2 = lemma_records[id2]
        A1 = compute_allomorphs(rec1["word"], rec1.get("pos",""), rec1.get("forms",[]))
        A2 = compute_allomorphs(rec2["word"], rec2.get("pos",""), rec2.get("forms",[]))
        D1 = _allomorphs_for_gates(rec1["word"], rec1.get("pos",""), rec1.get("forms",[]))
        D2 = _allomorphs_for_gates(rec2["word"], rec2.get("pos",""), rec2.get("forms",[]))
        
        f1 = accent_strip(rec1["word"]).lower()
        s1 = strip_one_prefix(f1)
        f2 = accent_strip(rec2["word"]).lower()
        s2 = strip_one_prefix(f2)
        
        print(f"\n=== Allomorph test (E3: plain set) ===")
        print(f"  {w1}: folded='{f1}', stripped='{s1}'")
        print(f"  {w2}: folded='{f2}', stripped='{s2}'")
        
        m1 = [a for a in A1 if len(a) >= 3 and s2.startswith(a)]
        m2 = [a for a in A2 if len(a) >= 3 and s1.startswith(a)]
        print(f"  {w2} starts with allomorph of {w1}: {m1[:5]}")
        print(f"  {w1} starts with allomorph of {w2}: {m2[:5]}")
        print(f"  Either passes (E3): {bool(m1 or m2)}")

        e1 = [a for a in D1 if len(a) >= 3 and s2.startswith(a)]
        e2 = [a for a in D2 if len(a) >= 3 and s1.startswith(a)]
        print(f"\n=== Allomorph test (E4: gated set with truncated stems) ===")
        print(f"  {w2} starts with allomorph of {w1}: {e1[:5]}")
        print(f"  {w1} starts with allomorph of {w2}: {e2[:5]}")
        print(f"  Either passes (E4): {bool(e1 or e2)}")
        
        # Check borrowed
        print(f"\n  {w1} in borrowed_lemmas: {id1 in builder.borrowed_lemmas}")
        print(f"  {w2} in borrowed_lemmas: {id2 in builder.borrowed_lemmas}")
        
        if not (m1 or m2):
            print("\n  *** DIAGNOSIS: ALLOMORPH TEST FAILS ***")
            print(f"  Checking prefix stripping for '{w2}':")
            # Show what happens with each prefix
            from pipeline.paradigm import _SPANISH_PREFIXES
            for pfx in _SPANISH_PREFIXES:
                if f2.startswith(pfx) and len(f2) > len(pfx) + 2:
                    candidate = f2[len(pfx):]
                    matches = [a for a in A1 if len(a) >= 3 and candidate.startswith(a)]
                    print(f"    strip '{pfx}' -> '{candidate}' matches={matches[:3]}")
        else:
            print("\n  *** DIAGNOSIS: ALLOMORPH TEST PASSES ***")
            print("  Edge should form unless blocked by hub/borrowed/eligibility check.")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        debug_e3(sys.argv[1], sys.argv[2])
    else:
        debug_e3("hacer", "hechizo")
