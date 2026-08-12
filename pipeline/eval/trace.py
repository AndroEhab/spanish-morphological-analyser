"""Extended trace tool: path finding, bridge analysis, ancestor diagnostics.

Usage:
  python -m pipeline.eval.trace --path hacer hacienda
  python -m pipeline.eval.trace --bridges picar
  python -m pipeline.eval.trace --ancestors hacer hacienda malhecho hazaña ahechar satisfacer
  python -m pipeline.eval.trace --edges conque queismo satisfacera
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict, deque

from pipeline.normalize import fold, accent_strip
from pipeline.etymology import parse_templates
from pipeline.paradigm import compute_allomorphs, strip_one_prefix, get_family_forming_buckets, compute_paradigm_key, build_paradigm_buckets
from pipeline.family import FamilyBuilder, _latin_root_keys, _is_usable_ancestor, _is_latin_ancestor, _allomorphs_for_gates

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_all():
    lemma_records = {}
    lemma_forms_raw = {}
    with open(DATA_DIR / "lemmas.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            lid = rec["id"]
            lemma_records[lid] = rec
            lemma_forms_raw[lid] = rec.get("forms", [])
    return lemma_records, lemma_forms_raw


def build_graph(lemma_records, lemma_forms_raw):
    """Build the edge graph exactly as FamilyBuilder does."""
    internal_edges = []
    etymon_edges = []
    etymtree_edges = []
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
    related_links = {}
    for lid, rec in lemma_records.items():
        dr = rec.get("derived", [])
        if dr:
            derived_links[lid] = dr
        rl = rec.get("related", [])
        if rl:
            related_links[lid] = rl
    builder.load_derived_links(derived_links)
    builder.load_related_links(related_links)

    builder._detect_hubs()
    # Build graph exactly as build() does
    graph: dict[int, set[tuple[int, str, str]]] = defaultdict(set)
    
    for lid in lemma_records:
        if not builder._eligible(lid):
            continue
        if builder.internal_degree.get(lid, 0) > 50:
            continue
        for pid, affix in builder.internal_parents.get(lid, []):
            if not builder._eligible(pid):
                continue
            if builder.internal_degree.get(pid, 0) > 50:
                continue
            mw = lemma_records[pid]["word"]
            if affix.endswith("-"):
                rlabel = f"{affix} + {mw}"
            elif affix.startswith("-"):
                rlabel = f"{mw} + {affix}"
            else:
                rlabel = affix if affix else "affix"
            if not rlabel:
                rlabel = "affix"
            graph[lid].add((pid, "affix", rlabel))
            graph[pid].add((lid, "affix", rlabel))

    for lid in lemma_records:
        lrec = lemma_records[lid]
        if lrec.get("pos") != "verb":
            continue
        l_rkey = builder.lemma_bucket.get(lid)
        if l_rkey is None:
            continue
        lP = builder.lemma_prefix.get(lid, "")
        for rid in builder.family_forming_buckets.get(l_rkey, ()):
            if rid <= lid:
                continue
            rrec = lemma_records[rid]
            if rrec.get("pos") != "verb":
                continue
            rP = builder.lemma_prefix.get(rid, "")
            if not lP or not rP:
                continue
            if len(lP) > len(rP):
                cP, hP, cid, hid = lP, rP, lid, rid
            elif len(rP) > len(lP):
                cP, hP, cid, hid = rP, lP, rid, lid
            else:
                continue
            if not cP.endswith(hP):
                h_keys = set()
                for anc in builder.lemma_ancestors.get(hid, ()):
                    h_keys.update(_latin_root_keys(anc))
                c_keys = set()
                for anc in builder.lemma_ancestors.get(cid, ()):
                    c_keys.update(_latin_root_keys(anc))
                if not (h_keys & c_keys):
                    c_folded = fold(lemma_records[cid]["word"])
                    h_folded = fold(lemma_records[hid]["word"])
                    if c_folded not in [fold(dw) for dw in derived_links.get(hid, [])] and \
                       h_folded not in [fold(dw) for dw in derived_links.get(cid, [])]:
                        continue
            hw = lemma_records[hid]["word"]
            rlabel = f"same paradigm as {hw}"
            graph[cid].add((hid, "paradigm", rlabel))
            graph[hid].add((cid, "paradigm", rlabel))

    for lid in lemma_records:
        if lid in builder.borrowed_lemmas:
            continue
        if not builder._eligible(lid):
            continue
        l_keys = set()
        for anc in builder.lemma_ancestors.get(lid, ()):
            for rk in _latin_root_keys(anc):
                if rk.endswith('T'):
                    l_keys.add(rk)
        if not l_keys:
            continue
        l_allos = compute_allomorphs(lemma_records[lid]["word"], lemma_records[lid].get("pos", ""), lemma_records[lid].get("forms", []))
        l_folded = accent_strip(lemma_records[lid]["word"]).lower()
        l_stripped = strip_one_prefix(l_folded)
        for rk in l_keys:
            if rk in builder.hub_root_keys:
                continue
            if len(builder.root_key_index.get(rk, ())) > 400:
                continue
            for rid in builder.root_key_index.get(rk, ()):
                if rid <= lid:
                    continue
                if rid in builder.borrowed_lemmas:
                    continue
                if not builder._eligible(rid):
                    continue
                r_allos = compute_allomorphs(lemma_records[rid]["word"], lemma_records[rid].get("pos", ""), lemma_records[rid].get("forms", []))
                r_folded = accent_strip(lemma_records[rid]["word"]).lower()
                r_stripped = strip_one_prefix(r_folded)
                ok = any(len(a) >= 3 and r_stripped.startswith(a) for a in l_allos) or \
                     any(len(a) >= 3 and l_stripped.startswith(a) for a in r_allos)
                if ok:
                    a_ancs = builder.lemma_ancestors.get(lid, set())
                    b_ancs = builder.lemma_ancestors.get(rid, set())
                    common = a_ancs & b_ancs
                    if common:
                        best = sorted(common, key=lambda x: -len(x))[0]
                        rlabel = f"inherited from Latin {best}"
                    else:
                        rlabel = f"same root as {lemma_records[lid]['word']}"
                    graph[lid].add((rid, "root-key", rlabel))
                    graph[rid].add((lid, "root-key", rlabel))

    for lid in lemma_records:
        if not builder._eligible(lid):
            continue
        l_allos = _allomorphs_for_gates(lemma_records[lid]["word"], lemma_records[lid].get("pos", ""), lemma_records[lid].get("forms", []))
        for dw in derived_links.get(lid, []):
            for rid in builder.word_index.get(fold(dw), []):
                if rid <= lid:
                    continue
                if not builder._eligible(rid):
                    continue
                r_folded = accent_strip(lemma_records[rid]["word"]).lower()
                r_stripped = strip_one_prefix(r_folded)
                if any(len(a) >= 3 and r_stripped.startswith(a) for a in l_allos):
                    rlabel = f"related to {lemma_records[lid]['word']}"
                    graph[lid].add((rid, "derived", rlabel))
                    graph[rid].add((lid, "derived", rlabel))

    return graph, builder


def find_lemma_id(lemma_records, word: str, pos: str = None) -> int | None:
    folded = fold(word)
    for lid, rec in lemma_records.items():
        if fold(rec["word"]) == folded:
            if pos is None or rec.get("pos") == pos:
                return lid
    return None


def find_path(graph, lemma_records, start_id, end_id):
    """BFS shortest path."""
    if start_id == end_id:
        return [(start_id, "self")]
    visited = {start_id}
    queue = deque([(start_id, [])])
    while queue:
        cur, path = queue.popleft()
        for other, rel, rlabel in graph.get(cur, ()):
            if other == end_id:
                return path + [(cur, rel, rlabel, other)]
            if other not in visited:
                visited.add(other)
                queue.append((other, path + [(cur, rel, rlabel, other)]))
    return None


def cmd_path(args_idx, lemma_records, graph, builder):
    if args_idx + 1 >= len(sys.argv):
        print("Usage: --path WORD1 WORD2")
        return
    w1, w2 = sys.argv[args_idx], sys.argv[args_idx + 1]
    id1 = find_lemma_id(lemma_records, w1)
    id2 = find_lemma_id(lemma_records, w2)
    if id1 is None:
        print(f"ERROR: '{w1}' not found")
        return
    if id2 is None:
        print(f"ERROR: '{w2}' not found")
        return
    path = find_path(graph, lemma_records, id1, id2)
    if path is None:
        print(f"No path found between {w1} and {w2}")
        return
    print(f"Path {w1} -> {w2} ({len(path)} hops):")
    for step in path:
        if len(step) == 2:
            print(f"  {lemma_records[step[0]]['word']} (self)")
        else:
            cur, rel, rlabel, nxt = step
            cw = lemma_records[cur]['word']
            nw = lemma_records[nxt]['word']
            print(f"  {cw} --[{rel}]--> {nw}  ({rlabel})")


def cmd_bridges(args_idx, lemma_records, graph, builder):
    word = sys.argv[args_idx]
    lid = find_lemma_id(lemma_records, word)
    if lid is None:
        print(f"ERROR: '{word}' not found")
        return
    # Find component
    visited = set()
    comp = set()
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
    print(f"Component containing '{word}': {len(comp)} members")
    # Find bridge edges (edges where removing them splits component)
    # Approximate: compute edge betweenness by BFS from each node
    # Simpler: just list edges by type
    edge_counts = defaultdict(int)
    edge_examples = defaultdict(list)
    for lid in comp:
        for other, rel, rlabel in graph.get(lid, ()):
            if other in comp and lid < other:
                edge_counts[rel] += 1
                if len(edge_examples[rel]) < 10:
                    cw = lemma_records[lid]['word']
                    nw = lemma_records[other]['word']
                    edge_examples[rel].append(f"{cw} <-> {nw}: {rlabel}")
    print(f"\nEdges by type:")
    for rel, count in sorted(edge_counts.items(), key=lambda x: -x[1]):
        print(f"  {rel}: {count}")
        for ex in edge_examples[rel][:5]:
            print(f"    {ex}")


def cmd_ancestors(args_idx, lemma_records, graph, builder):
    words = sys.argv[args_idx:]
    if not words:
        words = ["hacer", "hacienda", "malhecho", "hazaña", "ahechar", "satisfacer"]
    print(f"{'Word':<15} {'Lang':<8} {'Mode':<12} {'Ancestor':<25} {'StemKeys':<20} {'SupineKeys':<15}")
    print("-" * 100)
    for word in words:
        for lid, rec in lemma_records.items():
            if fold(rec["word"]) == fold(word):
                parsed = parse_templates(rec["word"], rec.get("etymology_templates", "[]"), rec.get("etymology_text", ""))
                for anc, lang, mode, src in parsed["etymons"]:
                    ks = _latin_root_keys(anc)
                    stem = [k for k in ks if not k.endswith('T')]
                    sup = [k for k in ks if k.endswith('T')]
                    print(f"{rec['word']:<15} {str(lang):<8} {mode:<12} {anc:<25} {str(stem):<20} {str(sup):<15}")
                for anc, lang in parsed["etymtree_ancestors"]:
                    ks = _latin_root_keys(anc)
                    stem = [k for k in ks if not k.endswith('T')]
                    sup = [k for k in ks if k.endswith('T')]
                    print(f"{rec['word']:<15} {str(lang):<8} {'tree':<12} {anc:<25} {str(stem):<20} {str(sup):<15}")
                break


def cmd_edges(args_idx, lemma_records, graph, builder):
    words = sys.argv[args_idx:]
    for word in words:
        lid = find_lemma_id(lemma_records, word)
        if lid is None:
            print(f"ERROR: '{word}' not found")
            continue
        rec = lemma_records[lid]
        print(f"\n=== {rec['word']} ({rec['pos']}) id={lid} ===")
        # Print source JSON data
        print(f"  head_templates: {rec.get('head_expansion','')[:100]}")
        print(f"  gloss: {rec.get('gloss','')}")
        print(f"  forms count: {len(rec.get('forms',[]))}")
        
        # Find edges in graph
        edges = graph.get(lid, set())
        if edges:
            print(f"  Edges ({len(edges)}):")
            for other, rel, rlabel in edges:
                orec = lemma_records.get(other, {})
                print(f"    --[{rel}]--> {orec.get('word','?')} ({orec.get('pos','?')}): {rlabel}")
        else:
            print(f"  No edges found in graph")
        
        # Check INTERNAL parents
        ips = builder.internal_parents.get(lid, [])
        if ips:
            print(f"  INTERNAL parents: {[(lemma_records.get(p,{}).get('word','?'), a) for p,a in ips]}")
        ics = builder.internal_children.get(lid, [])
        if ics:
            print(f"  INTERNAL children: {[(lemma_records.get(c,{}).get('word','?'), a) for c,a in ics]}")
        print(f"  Eligible: {builder._eligible(lid)}")
        print(f"  Borrowed: {lid in builder.borrowed_lemmas}")
        print(f"  Ancestors: {sorted(builder.lemma_ancestors.get(lid, set()))[:10]}")


if __name__ == "__main__":
    lemma_records, lemma_forms_raw = load_all()
    graph, builder = build_graph(lemma_records, lemma_forms_raw)

    if len(sys.argv) < 2:
        print("Usage: --path W1 W2 | --bridges W | --ancestors W... | --edges W...")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "--path":
        cmd_path(2, lemma_records, graph, builder)
    elif cmd == "--bridges":
        cmd_bridges(2, lemma_records, graph, builder)
    elif cmd == "--ancestors":
        cmd_ancestors(2, lemma_records, graph, builder)
    elif cmd == "--edges":
        cmd_edges(2, lemma_records, graph, builder)
    else:
        # Old mode: trace a single word
        word = cmd
        print(f"Use --path, --bridges, --ancestors, or --edges")
