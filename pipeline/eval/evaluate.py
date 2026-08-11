"""Evaluation script for the morphological analyser pipeline.

Run against the built data/morph.sqlite.
Usage: python -m pipeline.eval.evaluate
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "morph.sqlite"
GOLD_PATH = Path(__file__).resolve().parent / "gold_hacer.txt"


def load_gold() -> set[str]:
    with open(GOLD_PATH, encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip()}


def main():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run 'python -m pipeline.build' first.")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    db_size = DB_PATH.stat().st_size
    
    print("=" * 70)
    print("MORPHOLOGICAL ANALYSER — EVALUATION REPORT")
    print("=" * 70)
    
    # DB stats
    n_lemmas = conn.execute("SELECT COUNT(*) FROM lemma").fetchone()[0]
    n_forms = conn.execute("SELECT COUNT(*) FROM form").fetchone()[0]
    n_families = conn.execute("SELECT COUNT(*) FROM family").fetchone()[0]
    
    print(f"\nDB: {db_size / 1024 / 1024:.1f} MB, "
          f"{n_lemmas} lemmas, {n_forms} forms, {n_families} families")
    
    # ------------------------------------------------------------------
    # 1. HACER FAMILY
    # ------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("1. HACER FAMILY")
    print("-" * 70)
    
    gold = load_gold()
    
    # Find the hacer verb lemma
    hacer_lemma = conn.execute(
        "SELECT id, word, pos, family_id FROM lemma WHERE word = 'hacer' AND pos = 'verb'"
    ).fetchone()
    
    if not hacer_lemma:
        print("ERROR: 'hacer' (verb) lemma not found!")
        sys.exit(1)
    
    family_id = hacer_lemma["family_id"]
    if family_id is None:
        print("ERROR: 'hacer' has no family!")
        sys.exit(1)
    
    # Get all members
    members = conn.execute(
        """SELECT id, word, pos, relation_label, gloss,
                  (SELECT COUNT(*) FROM form WHERE lemma_id = lemma.id) AS form_count
           FROM lemma WHERE family_id = ?
           ORDER BY sort_key""",
        (family_id,),
    ).fetchall()
    
    family_words = {m["word"] for m in members}
    
    print(f"\nFamily ID: {family_id}, Head: hacer (verb)")
    print(f"Members: {len(members)}")
    print(f"\n{'Word':<20} {'POS':<10} {'Forms':>6}  Relation")
    print("-" * 70)
    for m in members:
        rel = m["relation_label"] or ""
        print(f"{m['word']:<20} {m['pos']:<10} {m['form_count']:>6}  {rel}")
    
    # Recall
    recalled = gold & family_words
    missing = gold - family_words
    extras = family_words - gold
    
    print(f"\n--- Recall ---")
    print(f"Gold: {len(gold)} words")
    print(f"Recalled: {len(recalled)} ({100*len(recalled)/len(gold):.0f}%)")
    if missing:
        print(f"MISSING: {sorted(missing)}")
    if extras:
        print(f"\nEXTRA (may be correct — same paradigm): {sorted(extras)}")
    
    # Assertion: factura, factor, efecto, facticio must NOT be in family
    forbidden = {"factura", "factor", "efecto", "facticio", "faena"}
    found_forbidden = forbidden & family_words
    if found_forbidden:
        print(f"\n*** BUG: Borrowed Latin words in hacer family: {found_forbidden} ***")
    else:
        print(f"\n*** PASS: No borrowed Latin words (factura, factor, efecto, facticio) in family ***")
    
    # ------------------------------------------------------------------
    # 2. mienta RESOLUTION
    # ------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("2. mienta — SENSE/LEMMA RESOLUTION")
    print("-" * 70)
    
    mienta_forms = conn.execute(
        """SELECT f.id, f.form, f.features, l.word AS lemma, l.pos
           FROM form f JOIN lemma l ON f.lemma_id = l.id
           WHERE f.key = 'mienta'"""
    ).fetchall()
    
    lemmas_seen = set()
    for mf in mienta_forms:
        feats = json.loads(mf["features"]) if mf["features"] else []
        if isinstance(feats, str):
            feats = [feats]
        print(f"  {mf['lemma']} ({mf['pos']}): {' | '.join(feats) if feats else '(no features)'}")
        lemmas_seen.add(mf["lemma"])
    
    if {"mentar", "mentir"}.issubset(lemmas_seen):
        print(f"  *** PASS: mienta resolves to both mentar and mentir ***")
    else:
        print(f"  *** BUG: mienta does NOT resolve to both mentar and mentir. Found: {lemmas_seen} ***")
    
    # ------------------------------------------------------------------
    # 3. SURFACE FORM SEARCHABILITY
    # ------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("3. SURFACE FORM SEARCHABILITY (hacer family)")
    print("-" * 70)
    
    test_forms = [
        "hizo", "hice", "hecho", "haz", "hacés", "hiciéremos",
        "hacerlo", "haciéndolo", "hazlo"
    ]
    
    for tf in test_forms:
        rows = conn.execute(
            """SELECT f.form, l.word AS lemma
               FROM form f JOIN lemma l ON f.lemma_id = l.id
               WHERE f.key = ? AND l.family_id = ?""",
            (tf.lower(), family_id),
        ).fetchall()
        
        if rows:
            lemmas = {r["lemma"] for r in rows}
            print(f"  FOUND: {tf} -> {lemmas}")
        else:
            print(f"  MISSING: {tf}")
    
    # ------------------------------------------------------------------
    # 4. OTHER FAMILY REPORTS
    # ------------------------------------------------------------------
    for lemma_name in ["mentir", "poner", "decir", "tener", "casa", "cantar"]:
        print("\n" + "-" * 70)
        print(f"4. {lemma_name.upper()} FAMILY")
        print("-" * 70)
        
        lemma_row = conn.execute(
            "SELECT id, word, pos, family_id FROM lemma WHERE word = ? LIMIT 1",
            (lemma_name,),
        ).fetchone()
        
        if not lemma_row or lemma_row["family_id"] is None:
            print(f"  Not found or no family.")
            continue
        
        fid = lemma_row["family_id"]
        fam_members = conn.execute(
            """SELECT word, pos, relation_label,
                      (SELECT COUNT(*) FROM form WHERE lemma_id = lemma.id) AS form_count
               FROM lemma WHERE family_id = ? ORDER BY sort_key""",
            (fid,),
        ).fetchall()
        
        fam_size = len(fam_members)
        
        # For cantar, check we didn't absorb the whole regular class
        if lemma_name == "cantar":
            print(f"  Members: {fam_size}")
            words = [m["word"] for m in fam_members]
            print(f"  Words: {', '.join(words[:30])}")
            if len(words) > 30:
                print(f"  ... and {len(words) - 30} more")
            if fam_size > 50:
                print(f"  *** WARNING: cantar family is large ({fam_size} members) — may have absorbed regular -ar class ***")
            else:
                print(f"  *** PASS: cantar family size {fam_size} — did NOT absorb full -ar class ***")
        else:
            print(f"  Members: {fam_size}")
            for m in fam_members[:25]:
                rel = m["relation_label"] or ""
                print(f"  {m['word']:<20} {m['pos']:<10} {m['form_count']:>4} forms  {rel}")
            if fam_size > 25:
                print(f"  ... and {fam_size - 25} more members")
    
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    
    conn.close()


if __name__ == "__main__":
    main()
