# SUBTLEX-ESP.xlsx — structure recon

## Sheet(s)

One sheet: **`Subtlex-Esp`** (only sheet in the workbook).

## Layout

- Dimensions `A1:O31453` → **31,453 rows** (1 header row + 31,452 data rows), 15 columns.
- The sheet holds **three side-by-side word lists** (alphabetically split), each a 5-column
  block with the SAME header. Blocks run to different last rows:

| block | columns | header | data rows | first word | last word | distinct words |
|---|---|---|---|---|---|---|
| 1 | A–E (A=Word, B=Freq. count, C=Freq. per million, D=Log freq., E=blank) | `Word, Freq. count, Freq. per million, Log freq., None` | 2–31,447 (31,446 rows) | `a` | `dinastías` | 31,409 |
| 2 | F–J (F=Word, G=Freq. count, H=Freq. per million, I=Log freq., J=blank) | same | 2–31,453 (31,452 rows) | `dinástico` | `notan` | 31,430 |
| 3 | K–O (K=Word, L=Freq. count, M=Freq. per million, N=Log freq., O=blank) | same | 2–31,441 (31,440 rows) | `nam` | `zurullos` | 31,422 |

- **Total distinct words: 94,261** (no cross-block overlap; blocks are disjoint word sets).
- Within-block duplicates: 76 words appear twice (e.g. `obligarías`, `dispárame`, `países`),
  i.e. 94,338 word rows vs 94,261 distinct.
- Header row is a single row: `('Word', 'Freq. count', 'Freq. per million', 'Log freq.', None, 'Word', 'Freq. count', 'Freq. per million', 'Log freq.', None, 'Word', 'Freq. count', 'Freq. per million', 'Log freq.', None)`.

## First 15 data rows (raw, block 1 = cols A–E; blocks 2/3 continue in parallel columns F–O)

| # | Word | Freq. count | Freq. per million | Log freq. |
|---|---|---|---|---|
| 1 | a | 965735 | 23214.783653846152 | 5.984858421018963 |
| 2 | aarón | 1040 | 25 | 3.017450729510536 |
| 3 | ábaco | 9 | 0.21634615384615383 | 1 |
| 4 | abad | 48 | 1.1538461538461537 | 1.6901960800285134 |
| 5 | abadesa | 12 | 0.28846153846153844 | 1.1139433523068367 |
| 6 | abadía | 95 | 2.2836538461538463 | 1.9822712330395682 |
| 7 | abajo | 8727 | 209.78365384615384 | 3.940914737580285 |
| 8 | abalancé | 4 | 0.09615384615384615 | 0.6989700043360187 |
| 9 | abalances | 2 | 0.04807692307692307 | 0.47712125471966244 |
| 10 | abalanza | 8 | 0.1923076923076923 | 0.9542425094393249 |
| 11 | abalanzaba | 2 | 0.04807692307692307 | 0.47712125471966244 |
| 12 | abalanzamos | 2 | 0.04807692307692307 | 0.47712125471966244 |
| 13 | abalanzan | 2 | 0.04807692307692307 | 0.47712125471966244 |
| 14 | abalanzándose | 2 | 0.04807692307692307 | 0.47712125471966244 |
| 15 | abalanzarán | 2 | 0.04807692307692307 | 0.47712125471966244 |

(The sheet's rows interleave 3 alphabetic runs side by side: row N holds block-1 word N,
block-2 word N, block-3 word N. E.g. row 1: `a` | `dinástico` | `notando`; row 13:
`abalanzan` | `dio` | `notarial`.)

## Columns to use

- **Word column**: `A` (block 1), `F` (block 2), `K` (block 3).
- **Frequency columns** (all usable):
  - `B/G/L` — **Freq. count** (raw integer occurrences)
  - `C/H/M` — **Freq. per million** (raw count / 41,600,000 × 1e6; base inferred consistently
    from e.g. `a`: 965735/23214.7836... × 1e6 = 41,600,000)
  - `D/I/N` — **Log freq.** (log10 of raw count)
- Columns E/J/O are blank. Headers repeated per block (not merged).

## Corpus note

Raw counts in the file sum to ≈40.0M (40,011,894 over distinct words; 40,017,237 over rows with
duplicates), while per-million values are normalized to a 41.6M-token corpus — so ~1.6M corpus
tokens' word types are not listed in this file (every row is complete: no word-without-count or
count-without-word rows).

## Target-word availability

Of the 29 recon words: present — hacer, hizo, hice, hecho, mienta, mentir, deshacer, rehacer,
satisfacer, hechizo, hechizar, hechicero, hacienda, hacedor, malhechor, quehacer, factura,
factor, efecto, cantar, canté, comer, vivir, casa, casita, correr. **Missing from SUBTLEX**:
`mentar`, `hacendado`, `hechura` (not among the 94,261 listed words).
