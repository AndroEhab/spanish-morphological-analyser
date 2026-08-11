"""Create a small subset of the JSONL for fast iteration.

Filters entries reachable from a seed word list + their immediate surroundings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _fold(text: str) -> str:
    import unicodedata
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFC", text).casefold())
    return "".join(ch for ch in decomposed if not (0x0300 <= ord(ch) <= 0x036F))


def create_subset(
    jsonl_path: Path,
    output_path: Path,
    seed_words: set[str],
    expand_forms: bool = True,
):
    """Create a subset by capturing lemma entries and linked form entries."""
    seed_folded = {_fold(w) for w in seed_words}
    
    # Pass 1: collect all lemma words we want
    keep_words: set[str] = set(seed_folded)
    
    if expand_forms:
        # Also capture form-of entries pointing to seed words
        print("Scanning for form-of entries linking to seed words...")
        extra_lemmas: set[str] = set()
        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                senses = entry.get("senses") or []
                for sense in senses:
                    tags = sense.get("tags") or []
                    if "form-of" not in tags and "alt-of" not in tags:
                        continue
                    form_of = sense.get("form_of") or []
                    if not form_of:
                        continue
                    lemma_word = form_of[0].get("word", "")
                    if _fold(lemma_word) in seed_folded:
                        keep_words.add(_fold(entry.get("word", "")))
                        break
        print(f"  Added {len(extra_lemmas)} extra form words")
    
    # Pass 2: write filtered entries
    written = 0
    with open(jsonl_path, encoding="utf-8") as fh, \
         open(output_path, "w", encoding="utf-8") as out:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            word = entry.get("word", "")
            folded = _fold(word)
            
            if folded in keep_words:
                out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                written += 1
                continue
            
            # Also keep entries whose form_of points to seed words
            senses = entry.get("senses") or []
            for sense in senses:
                tags = sense.get("tags") or []
                if "form-of" not in tags and "alt-of" not in tags:
                    continue
                form_of = sense.get("form_of") or []
                if not form_of:
                    continue
                lemma_word = form_of[0].get("word", "")
                if _fold(lemma_word) in seed_folded:
                    out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    written += 1
                    break
    
    print(f"Wrote {written} entries to {output_path}")


if __name__ == "__main__":
    # Default seed words covering the hacer family + test words
    seeds = {
        "hacer", "deshacer", "rehacer", "satisfacer", "contrahacer",
        "hacedor", "hacedero", "quehacer", "hechura", "hechor",
        "hecho", "malhecho", "malhechor", "hechizo", "hechizar",
        "hechicero", "hechicería", "hacienda", "hacendar", "hacendado",
        "factura", "factor", "efecto", "facticio", "faena",
        "mentar", "mentir", "mienta", "cantar", "poner", "decir",
        "tener", "casa", "vivir", "bendecir", "bailar",
        # Additional words for broader testing
        "comer", "correr",
    }
    
    jsonl = Path("kaikki.org-dictionary-Spanish.jsonl")
    output = Path("data/subset.jsonl")
    
    if not jsonl.exists():
        print(f"ERROR: {jsonl} not found", file=sys.stderr)
        sys.exit(1)
    
    create_subset(jsonl, output, seeds, expand_forms=True)
