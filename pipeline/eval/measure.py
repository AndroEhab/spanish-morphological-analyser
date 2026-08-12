"""Population measurement for family-graph variants.

Reproduces the exact FamilyBuilder build (as build.py does) and reports
singleton counts, family-size distributions, and largest families.  The
`_MIN_TRUNC_STEM` gate (truncated-stem allomorphs admitted to the E4/E4b
derived/related gates) is the only knob varied.

Usage:
  python -m pipeline.eval.measure current           # as shipped (min 4)
  python -m pipeline.eval.measure baseline          # truncation disabled
  python -m pipeline.eval.measure trunc <min_len>   # alternate gate
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import pipeline.family as fam_mod
from pipeline.family import FamilyBuilder
from pipeline.etymology import parse_templates

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
FREQ_PATH = Path(__file__).resolve().parent.parent.parent / "es_full.txt"


def load_all() -> tuple[dict[int, dict], dict[int, list]]:
    lemma_records: dict[int, dict] = {}
    lemma_forms_raw: dict[int, list] = {}
    with open(DATA_DIR / "lemmas.jsonl", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            lid = rec["id"]
            lemma_records[lid] = rec
            lemma_forms_raw[lid] = rec.get("forms", [])
    from pipeline.frequency import load as load_frequency
    freq_map = load_frequency(FREQ_PATH)
    for lid, rec in lemma_records.items():
        rec["freq"] = freq_map.get(rec["word"].lower(), 0.0)
    return lemma_records, lemma_forms_raw


def make_builder(lemma_records: dict, lemma_forms_raw: dict) -> FamilyBuilder:
    internal_edges, etymon_edges, etymtree_edges = [], [], []
    for lid, rec in lemma_records.items():
        parsed = parse_templates(
            rec["word"], rec.get("etymology_templates", "[]"), rec.get("etymology_text", "")
        )
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

    derived_links: dict[int, list[str]] = {}
    related_links: dict[int, list[str]] = {}
    for lid, rec in lemma_records.items():
        dr = rec.get("derived", [])
        if dr:
            derived_links[lid] = dr
        rl = rec.get("related", [])
        if rl:
            related_links[lid] = rl
    builder.load_derived_links(derived_links)
    builder.load_related_links(related_links)
    return builder


def report(tag: str, lemma_records: dict, builder: FamilyBuilder) -> None:
    sizes = Counter()
    for fam in builder.families.values():
        sizes[len(fam["members"])] += 1
    singleton_lids = [
        lid
        for fam in builder.families.values()
        if len(fam["members"]) == 1
        for lid in fam["members"]
    ]
    total_lemmas = len(lemma_records)
    print(f"[{tag}] lemmas={total_lemmas} families={len(builder.families)} "
          f"singletons={len(singleton_lids)} ({100.0 * len(singleton_lids) / total_lemmas:.1f}%)")
    top = sorted(sizes.items(), key=lambda x: -x[0])[:8]
    print(f"[{tag}] family-size dist (top sizes): {top}")
    max_size = max(sizes)
    big = [fid for fid, fam in builder.families.items() if len(fam["members"]) == max_size]
    for fid in big:
        head = lemma_records[builder.families[fid]["head_id"]]["word"]
        print(f"[{tag}] largest family: {max_size} members, head={head}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "current"
    if mode == "baseline":
        fam_mod._MIN_TRUNC_STEM = 999
    elif mode == "trunc":
        fam_mod._MIN_TRUNC_STEM = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    t0 = time.time()
    lemma_records, lemma_forms_raw = load_all()
    print(f"loaded {len(lemma_records)} lemmas in {time.time() - t0:.1f}s")
    builder = make_builder(lemma_records, lemma_forms_raw)
    builder.build(reject_log_path=None)
    report(mode.upper(), lemma_records, builder)


if __name__ == "__main__":
    main()
