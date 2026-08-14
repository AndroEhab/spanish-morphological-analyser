"""FIXTURE BACKEND — replaced by the SQLite store once the pipeline lands.

Data access layer for the morphological analyser. All data currently comes
from a hand-authored JSON fixture at ``app/fixtures/sample.json``; the
loading, indexing and lookup logic below is deliberately isolated in this
module so that swapping in the real SQLite store touches only this file.

The ``probar`` family in the fixture is SYNTHETIC STRESS-TEST SCAFFOLDING:
it is not drawn from the real pipeline, and exists only to exercise UI
limits (a POS group with 15+ members, a member with 300+ forms, uncommon
POS tags ``name``/``phrase``, and a very long gloss).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from unicodedata import normalize

from app import enrich

_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "sample.json"

# POS group order for the family view: verb, noun, adj, adv, then anything
# else alphabetically. Empty groups are omitted by the backend.
_GROUP_ORDER = ["verb", "noun", "adj", "adv"]

_POS_LABELS = {
    "verb": "Verbs",
    "noun": "Nouns",
    "adj": "Adjectives",
    "adv": "Adverbs",
    "name": "Names",
    "phrase": "Phrases",
}


def _fold(text: str) -> str:
    """Lowercase and strip diacritics so matching is case- and accent-insensitive."""
    decomposed = normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not _is_combining(ch))


def _is_combining(ch: str) -> bool:
    return 0x0300 <= ord(ch) <= 0x036F


@lru_cache(maxsize=1)
def _load() -> dict:
    """Load the fixture once and build the search/analyze indexes."""
    with open(_FIXTURE_PATH, encoding="utf-8") as fh:
        fixture = json.load(fh)

    families = fixture["families"]
    for family in families:
        head_lemma = family["head"]
        for member in family["members"]:
            member["is_head"] = member["lemma"] == head_lemma

    # Flat search index: one record per (form, lemma, pos).
    entries: list[dict] = []
    by_id: dict[str, dict] = {}
    lemmas: set[str] = set()
    for family in families:
        for member in family["members"]:
            lemmas.add(member["lemma"])
            for form in member["forms"]:
                entry = {
                    "id": f'{form["form"]}::{member["lemma"]}::{member["pos"]}',
                    "form": form["form"],
                    "folded": _fold(form["form"]),
                    "lemma": member["lemma"],
                    "pos": member["pos"],
                    "label": form["form"],
                    "gloss": member["gloss"],
                    "freq": form["freq"],
                    "is_lemma": form["is_lemma"],
                    "features": list(form["features"]),
                    "family": family,
                    "member": member,
                }
                entries.append(entry)
                by_id[entry["id"]] = entry

    return {
        "families": families,
        "entries": entries,
        "by_id": by_id,
        "lemmas": lemmas,
    }


def _public_row(entry: dict) -> dict:
    """Project one indexed entry onto the frozen API search-row shape."""
    return {
        "id": entry["id"],
        "form": entry["form"],
        "lemma": entry["lemma"],
        "pos": entry["pos"],
        "label": entry["label"],
        "gloss": entry["gloss"],
        "freq": entry["freq"],
        "is_lemma": entry["is_lemma"],
        "features": list(entry["features"]),
    }


def _coarse_relation(relation: str) -> str:
    """Map a fixture member relation onto the coarse tree relation kinds."""
    if relation == "root":
        return "root"
    if relation.startswith(("prefix:", "suffix:")) or relation == "participle":
        return "affix"
    if relation.startswith("inherited"):
        return "inherited"
    if relation.startswith("same paradigm"):
        return "same paradigm"
    return relation


def _member_freq(member: dict) -> float:
    """Corpus frequency of the member's citation form (fall back to the
    most frequent form when no form is flagged as the lemma)."""
    for form in member["forms"]:
        if form["is_lemma"]:
            return form["freq"]
    return max((form["freq"] for form in member["forms"]), default=0.0)


def _relation_label(relation: str, head_lemma: str) -> str:
    """Human-readable derivation label for a fixture member relation."""
    if relation == "root":
        return "root"
    if relation.startswith("prefix:"):
        return f"{relation[7:]} + {head_lemma}"
    if relation.startswith("suffix:"):
        return f"{head_lemma} + {relation[7:]}"
    return relation


def _tree_view(family: dict, entry: dict) -> dict:
    """Derivation tree per the frozen API contract.

    Families with an explicit ``tree`` in the fixture use it verbatim,
    enriched with member data (pos, gloss, freq, form count). Families
    without one synthesize a star — every non-head member hangs off the
    head — which is the degenerate shape the UI must handle anyway.
    """
    by_key = {(m["lemma"], m["pos"]): m for m in family["members"]}
    spec = family.get("tree")
    if spec:
        nodes_spec = list(spec["nodes"])
        root_id = spec.get("root_lemma_id")
    else:
        head = next(m for m in family["members"] if m["is_head"])
        ids: dict[tuple[str, str], int] = {}

        def nid(member: dict) -> int:
            key = (member["lemma"], member["pos"])
            if key not in ids:
                ids[key] = len(ids) + 1
            return ids[key]

        head_id = nid(head)
        nodes_spec = [
            {
                "lemma_id": head_id,
                "lemma": head["lemma"],
                "pos": head["pos"],
                "parent_id": None,
                "relation": "root",
                "label": "root",
            }
        ]
        for member in family["members"]:
            if member["is_head"]:
                continue
            nodes_spec.append(
                {
                    "lemma_id": nid(member),
                    "lemma": member["lemma"],
                    "pos": member["pos"],
                    "parent_id": head_id,
                    "relation": _coarse_relation(member["relation"]),
                    "label": _relation_label(member["relation"], head["lemma"]),
                }
            )
        root_id = head_id

    # Depth is derivable in one pass because tree.nodes is depth-first and
    # every parent precedes its children (frozen contract).
    depth_by_id: dict[int, int] = {}
    for node in nodes_spec:
        pid = node["parent_id"]
        depth_by_id[node["lemma_id"]] = 0 if pid is None else depth_by_id.get(pid, 0) + 1

    nodes = []
    for node in nodes_spec:
        member = by_key.get((node["lemma"], node.get("pos", "")))
        nodes.append(
            {
                "lemma_id": node["lemma_id"],
                "lemma": node["lemma"],
                "pos": (member or node).get("pos", ""),
                "gloss": (member or node).get("gloss", ""),
                "parent_id": node["parent_id"],
                "relation": node["relation"],
                "label": node["label"],
                "depth": depth_by_id[node["lemma_id"]],
                "freq": _member_freq(member) if member else node.get("freq", 0),
                "form_count": len(member["forms"]) if member else node.get("form_count", 0),
                "is_selected": bool(member)
                and member["lemma"] == entry["lemma"]
                and member["pos"] == entry["pos"],
            }
        )
    return {"root_lemma_id": root_id, "nodes": nodes}


def _ancestry_view(family: dict, entry: dict) -> list[dict]:
    """Etymological chain for the selected entry, oldest step last in the
    payload (the word itself first), matching the frozen contract example.
    Per-lemma overrides win over the family default; absent data is []."""
    by_lemma = family.get("ancestry_by_lemma") or {}
    return by_lemma.get(entry["lemma"], family.get("ancestry") or [])


def _apply_qualifiers(rows: list[dict]) -> list[dict]:
    """Set ``qualifier`` (the row's own lemma) on rows whose surface form maps
    to more than one lemma among the returned candidates."""
    forms_with_many_lemmas: set[str] = set()
    seen: dict[str, set[str]] = {}
    for row in rows:
        seen.setdefault(row["form"], set()).add(row["lemma"])
    for form, lemmas in seen.items():
        if len(lemmas) > 1:
            forms_with_many_lemmas.add(form)
    out = []
    for row in rows:
        out.append({**row, "qualifier": row["lemma"] if row["form"] in forms_with_many_lemmas else None})
    return out


def search(q: str, limit: int) -> list[dict]:
    """Tiered, deterministic match over folded (case/accent-insensitive) keys:

    - tier 0: folded form == folded query (exact form match)
    - tier 1: folded form startswith query
    - tier 2: folded form contains query

    Within a tier: frequency descending, then form length ascending, then
    form ascending, then lemma ascending. Rows for the same surface form
    (different lemmas) are always adjacent, and the limit cuts whole
    surface-form groups — a group is fully included or fully dropped,
    never split across the boundary.
    """
    q = q.strip()
    if not q:
        return []
    folded = _fold(q)
    data = _load()

    # Group matching entries by surface form. All rows of one form share a
    # folded key, hence a tier; the group takes that tier.
    groups: dict[str, dict] = {}
    for entry in data["entries"]:
        fk = entry["folded"]
        if fk == folded:
            tier = 0
        elif fk.startswith(folded):
            tier = 1
        elif folded in fk:
            tier = 2
        else:
            continue
        groups.setdefault(entry["form"], {"tier": tier, "entries": []})
        groups[entry["form"]]["entries"].append(entry)

    def group_key(item: tuple[str, dict]) -> tuple:
        form, group = item
        best = max(e["freq"] for e in group["entries"])
        return (group["tier"], -best, len(form), form)

    ordered: list[list[dict]] = []
    for form, group in sorted(groups.items(), key=group_key):
        group["entries"].sort(key=lambda e: (-e["freq"], len(e["form"]), e["form"], e["lemma"]))
        ordered.append(group["entries"])

    selected: list[dict] = []
    remaining = limit
    for group in ordered:
        if len(group) <= remaining:
            selected.extend(group)
            remaining -= len(group)
        else:
            break

    rows = [_public_row(e) for e in selected]
    return _apply_qualifiers(rows)


def analyze(entry_id: str) -> dict | None:
    """Family view for a single dictionary entry id; ``None`` -> 404."""
    entry = _load()["by_id"].get(entry_id)
    if entry is None:
        return None

    family = entry["family"]
    head = next(m for m in family["members"] if m["is_head"])

    def member_view(member: dict) -> dict:
        return {
            "lemma": member["lemma"],
            "gloss": member["gloss"],
            "relation": member["relation"],
            "relation_label": _relation_label(member["relation"], head["lemma"]),
            "is_head": member["is_head"],
            "forms": [
                {
                    "form": f["form"],
                    "features": " \u00b7 ".join(f["features"]),
                    "is_lemma": f["is_lemma"],
                }
                for f in member["forms"]
            ],
        }

    # Group members by POS in canonical order; empty groups are omitted.
    by_pos: dict[str, list[dict]] = {}
    for member in family["members"]:
        by_pos.setdefault(member["pos"], []).append(member_view(member))
    extra = sorted(pos for pos in by_pos if pos not in _GROUP_ORDER)
    group_order = [pos for pos in _GROUP_ORDER + extra if pos in by_pos]

    groups = [
        {
            "pos": pos,
            "pos_label": _POS_LABELS.get(pos, f"{pos}s".capitalize()),
            "members": by_pos[pos],
        }
        for pos in group_order
    ]

    # ---- Phase 1 dashboard enrichment (docs/DESIGN_IMPLEMENTATION_PLAN.md §D) ----
    # Additive and nullable; the empty values are the empty-state triggers.
    member = entry["member"]
    known_forms = [(f["form"], list(f["features"])) for f in member["forms"]]
    parts = enrich.pick_clean_analysis(entry["features"])
    if entry["pos"] == "verb":
        stem, desinence = enrich.split_lexeme(
            entry["form"], parts, known_forms, list(entry["features"])
        )
    else:
        stem, desinence = None, None
    pos_label = enrich.spanish_pos_label(entry["pos"])
    conjugation = enrich.conjugation_class(entry["lemma"], entry["pos"])
    morphology = {
        "posLabel": pos_label,
        "summary": enrich.spanish_summary(entry["pos"], entry["features"]),
        "lexeme": f"{stem}-" if stem else None,
        "inflection": f"-{desinence}" if desinence else None,
        "base": entry["lemma"],
        "categoría": pos_label,
        "conjugationClass": conjugation,
        "conjugación": conjugation,
        "decomposition": enrich.decomposition_items(
            entry["form"], stem, desinence, list(entry["features"])
        ),
        "alternatives": _fixture_alternatives(entry),
    }

    def coarse_priority(relation: str) -> int:
        coarse = _coarse_relation(relation)
        return {"affix": 0, "same paradigm": 1, "inherited": 2}.get(coarse, 4)

    # Stable per-family node ids keyed by (lemma, pos), mirroring _tree_view.
    node_ids: dict[tuple[str, str], int] = {}

    def nid(key: tuple[str, str]) -> int:
        if key not in node_ids:
            node_ids[key] = len(node_ids) + 1
        return node_ids[key]

    family_preview = enrich.family_preview(
        {
            "lemma": head["lemma"],
            "pos": head["pos"],
            "gloss": head["gloss"],
            "lemma_id": nid((head["lemma"], head["pos"])),
        },
        [
            {
                "lemma_id": nid((m["lemma"], m["pos"])),
                "lemma": m["lemma"],
                "pos": m["pos"],
                "gloss": m["gloss"],
                "relation": m["relation"],
                "relation_label": _relation_label(m["relation"], head["lemma"]),
                "freq": _member_freq(m),
                "is_head": m["is_head"],
                "relation_priority": coarse_priority(m["relation"]),
            }
            for m in family["members"]
        ],
        nid((entry["lemma"], entry["pos"])),
        entry["form"],
        entry["pos"],
        entry["gloss"],
        len(family["members"]),
    )

    return {
        "query": entry["form"],
        "selected": {
            "id": entry["id"],
            "form": entry["form"],
            "lemma": entry["lemma"],
            "pos": entry["pos"],
            "gloss": entry["gloss"],
            "features": list(entry["features"]),
            "audio": None,  # Phase 2 (Spanish-edition sounds import)
            "ipa": None,    # Phase 2
        },
        "family": {
            "head": {"lemma": head["lemma"], "pos": head["pos"], "gloss": head["gloss"]},
            "note": family["note"],
            "groups": groups,
        },
        "tree": _tree_view(family, entry),
        "ancestry": _ancestry_view(family, entry),
        "cousins": family.get("cousins"),
        "morphology": morphology,
        "familyPreview": family_preview,
        "origin": enrich.origin_view(_ancestry_view(family, entry)),
        "nearbyForms": enrich.nearby_forms(
            entry["pos"], entry["features"],
            [
                {
                    "form": f["form"],
                    "features": list(f["features"]),
                    "is_clitic": False,
                    "is_lemma": bool(f["is_lemma"]),
                }
                for f in member["forms"]
            ],
        ),
        "englishRelatives": family.get("englishRelatives"),
        "mnemonics": None,         # Phase 4
    }


def _fixture_alternatives(entry: dict) -> list[dict]:
    """Ranked alternative analyses of the same surface form under other
    lemmas (design.md §16: "Other possible analysis (1)")."""
    data = _load()
    per_lemma: dict[tuple[str, str], list] = {}
    for e in data["entries"]:
        if e["folded"] == entry["folded"] and (e["lemma"], e["pos"]) != (entry["lemma"], entry["pos"]):
            per_lemma.setdefault((e["lemma"], e["pos"]), []).append(e)
    ranked = []
    for (lemma, pos), group in per_lemma.items():
        best = max(group, key=lambda e: (e["freq"], e["id"]))
        ranked.append((best["freq"], {
            "lemma": lemma,
            "pos": pos,
            "summary": enrich.spanish_summary(pos, best["features"]),
            "entry_id": best["id"],
        }))
    ranked.sort(key=lambda item: (-item[0], item[1]["lemma"]))
    return [item[1] for item in ranked]


def health() -> dict:
    data = _load()
    return {
        "status": "ok",
        "entries": len(data["entries"]),
        "lemmas": len(data["lemmas"]),
        "families": len(data["families"]),
    }
