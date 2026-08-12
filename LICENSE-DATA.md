# Data Licence — Spanish Morphological Analyser

The source code in this repository is licensed under the MIT License — see
[`LICENSE`](LICENSE). The **linguistic content** is licensed separately and
**cannot be relicensed**: it derives from CC BY-SA 4.0 sources and carries
its own attribution and share-alike obligations regardless of what the code
licence says.

## What the content licence covers

- **`app/fixtures/sample.json`** — the bundled demo fixture. Its glosses are
  abridged/lightly reworded from English Wiktionary (one verbatim); its
  frequency figures are hand-invented demo values, not FrequencyWords data.
  The gloss content is licensed under **CC BY-SA 4.0**.
- **`data/morph.sqlite`** — the built database (not shipped in this
  repository). It is a derivative of English Wiktionary (via the kaikki.org
  extraction) and of the hermitdave/FrequencyWords Spanish frequency list
  (OpenSubtitles-derived). Both sources are **CC BY-SA 4.0**, so the
  database is **CC BY-SA 4.0**: redistributing it requires attribution to
  both sources, a link to the licence, a statement that it was modified,
  and release of any adapted version under the same (or a compatible)
  licence (share-alike).

## Source datasets

Neither source dataset is shipped in this repository. Rebuilders obtain them
from their primary sources under their respective terms:

- <https://kaikki.org/dictionary/Spanish/> — kaikki.org wiktextract
  extraction of English Wiktionary
- <https://github.com/hermitdave/FrequencyWords> — Spanish frequency list
  (`content/2018/es/es_full.txt`)

## Attribution

- Wiktionary/kaikki:
  "Word data derived from [English Wiktionary](https://en.wiktionary.org)
  via the [kaikki.org Spanish extraction](https://kaikki.org/dictionary/Spanish/),
  licensed under the [Creative Commons Attribution-ShareAlike 4.0
  International](https://creativecommons.org/licenses/by-sa/4.0/) and the
  [GNU Free Documentation License](https://www.gnu.org/licenses/fdl-1.3.html)
  (dual-licensed; text modified/extracted). Wiktionary: Tatu Ylonen,
  'Wiktextract: Wiktionary as Machine-Readable Structured Data', LREC 2022."
- FrequencyWords:
  "Frequency data from the [FrequencyWords](https://github.com/hermitdave/FrequencyWords)
  Spanish frequency list (`content/2018/es/es_full.txt`,
  OpenSubtitles-derived, © Hermit Dave and contributors), licensed under the
  [Creative Commons Attribution-ShareAlike 4.0
  International](https://creativecommons.org/licenses/by-sa/4.0/) License
  (per the repository: 'MIT License for code. CC-by-sa-4.0 for content.')."

## Full audit

See [`docs/LICENSES.md`](docs/LICENSES.md) for the complete licensing audit
(package licences, verbatim data terms, and the obligations per distribution
scenario).
