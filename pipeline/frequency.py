"""FrequencyWords (OpenSubtitles) frequency loader.

Reads hermitdave/FrequencyWords `content/2018/es/es_full.txt`
(https://github.com/hermitdave/FrequencyWords) — one `word<space>count`
entry per line, lowercase, accents preserved, raw OpenSubtitles-derived
counts. The frequency data is licensed CC BY-SA 4.0.

Normalises to per-million: freq_pm = count / corpus_total * 1_000_000,
preserving the exact semantics of `form.freq` ("occurrences per million")
that the DB and all downstream ranking assume. The corpus total is the sum
of every valid count line in the file.

Corpus total for the current es_full.txt (as of 2026-08-12):
423,290,924 tokens over 1,202,520 distinct words (0 malformed lines).

Produces word -> per-million float (duplicate entries summed).
"""

from __future__ import annotations

import sys
from pathlib import Path


def load(txt_path: str | Path) -> dict[str, float]:
    counts: dict[str, int] = {}
    n_lines = 0
    skipped = 0

    with open(txt_path, encoding="utf-8") as fh:
        for line in fh:
            n_lines += 1
            parts = line.strip().rsplit(None, 1)
            if len(parts) != 2 or not parts[0]:
                skipped += 1
                continue
            word, count_str = parts
            try:
                count = int(count_str)
            except ValueError:
                skipped += 1
                continue
            if count < 0:
                skipped += 1
                continue
            key = word.lower()
            counts[key] = counts.get(key, 0) + count

    total = sum(counts.values())
    freq = {word: count / total * 1_000_000.0 for word, count in counts.items()}

    print(f"frequency: {skipped} malformed line(s) skipped "
          f"({n_lines} lines, {len(freq)} distinct words, "
          f"corpus total {total})", file=sys.stderr)
    return freq
