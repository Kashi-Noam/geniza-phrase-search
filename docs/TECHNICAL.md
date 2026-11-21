# Geniza Phrase Search: technical documentation

This document explains how the phrase search is built, from the raw transcriptions to the page in the browser, and how to rebuild or change it.

The cleaning rules for each transcription convention are documented separately in [transcription_conventions.md](transcription_conventions.md).

## 1. Overview

```
 FIST database (SQL Server)         princetongenizalab/pgp-text (git)
 dbo.zzTransForRosetta              */*/PGPID*_transcription.html
        │ extract_fgp.py                      │
        ▼                                     │
 ngram_fgp_raw.parquet ──────────┐            │
 ngram_fgp_not_public.parquet    │            │
                                 ▼            ▼
 geniza_fragments_status.parquet ──►  corpus.py  ──► corpus_lines.parquet   (one row per cleaned line)
 (dashboard table: MMS, shelfmark,                          │
  library, unified genre)                                   ▼
                                                       phrases.py ──► phrases.duckdb   (phrases + counts + lines)
                                                            │                   │
                                                            ▼                   ▼
                                                    export_static.py     local-app/  (Python server, exact counts)
                                                            │
                                                            ▼
                                                 data/  +  index.html   (GitHub Pages: the search runs in the browser)
```

There are two ways to use it:

- **Online** (this repository, GitHub Pages): a static site. The browser downloads only the compressed data files it needs and does the matching itself in JavaScript. There is no server.
- **Local app** (`local-app/`): a small Python web server over `phrases.duckdb`, using DuckDB. It has the same interface, gives exact example counts, and is useful for development or for large batch queries from Python.

All pipeline scripts run on the Haifa server in `/nas/archive/haifa-data/noam/fgp_report/`. The paths are set at the top of each script.

## 2. Repository layout

| Path | What it is |
|---|---|
| `index.html` | The online page: interface plus the in-browser search engine |
| `data/` | Static data files produced by `pipeline/export_static.py` (section 6) |
| `pipeline/extract_fgp.py` | Exports the Friedberg transcriptions from the FIST database |
| `pipeline/sq.py` | Connection helper for the SQL Server restored from the FIST backup |
| `pipeline/corpus.py` | Parses and cleans all transcriptions into lines |
| `pipeline/phrases.py` | Counts 2–7-word phrases into `phrases.duckdb` |
| `pipeline/export_static.py` | Turns `phrases.duckdb` into the files in `data/` |
| `local-app/` | The Python version: `app.py` (server), `search.py` (search functions and command line), `index.html`, `start.command` |
| `docs/transcription_conventions.md` | Markup survey and cleaning rules |

## 3. Sources

| | Princeton Geniza Project | Friedberg Genizah Project |
|---|---|---|
| Origin | `github.com/princetongenizalab/pgp-text` (HTML exports) | FIST database backup (`FIST_28_1_26.bak`), table `dbo.zzTransForRosetta` |
| Licence | CC BY-NC 4.0 | Per transcription (fields `HebCopyRight` / `EngCopyRight`); published with permission |
| Transcriptions | 8,524 | 51,922; minus 4,714 copies of Princeton texts and 27 not on the public website |
| Words | 1.9 M | 14.2 M |
| Line breaks | Kept (`<li>` per line, `<h3>` block labels) | Lost in 85% of rows; restored for Genuzot from in-text markers |

Every transcription is linked to the dashboard's fragment table (`geniza_fragments_status.parquet`), by Princeton document id or by FGP inventory id. The link supplies the NLI record (MMS), the shelfmark, the library and the unified genre (domain and genre).

### Excluded material

- **Translations.**
- **FGP rows marked "Documentation for Princeton documents".** They duplicate Princeton, and the Princeton copy has the line structure.
- **FGP transcriptions that are not in the public website snapshot.** The snapshot (`SnpShot.UnitTran`) contains only view levels 0 and 310. Records marked 2310 ("allowed users only") or 3310 ("not for publication") are not in it, so they are left out.
- **The automatic (HTR) transcriptions.** They are left out on purpose, because their noise would distort the counts.

## 4. Cleaning (`corpus.py`)

Each transcription is split into lines. Each line is turned into two versions:

- **strict**: only letters that can be read on the fragment. A word with any letter restored by the editor is dropped, and expanded abbreviations are reduced to what is written.
- **full**: including the editor's restorations and expansions.

Both versions replace gaps with a break mark `‖`. A phrase is never counted across a break.

### Steps for one line (`clean_line`)

1. **Decode and normalize.** Decode HTML entities. Unify `׳ ״ \``, curly quotes and maqaf.
2. **Repair FGP export damage.** Collapse tripled prefix letters, for example `לללדונו` → `לדונו`.
3. **Remove editor material:**
   - section labels (`העתקות א`, `צד א'`);
   - variants `(x ){y`, keeping the corrected reading;
   - unclosed Bible references `(תה' פה יא`;
   - typed-in editor notes (`הערות שורה`, `יש הערת גליון`, `ראה אוצר`), limited to 12 words each;
   - scribal deletions (`⟦ ⟧`, `[[ ]]`, `<del>`);
   - parenthesized notes.
4. **Flag the line as uncertain** if it had `?` or `^` (doubtful letters).
5. **Turn gaps into one internal mark:** `[ ]`, `[...]`, dot runs, `[ּ ּ]`, `--`, `|`.
6. **Balance brackets** (`balance`):
   - a `[` or `]` with no partner marks the broken edge of the fragment, so it becomes a gap;
   - a mirrored pair `]x[` inside one word (a right-to-left export artifact) is swapped back.
7. **Mark editorial insertions.** A short `<...>` inside a line, up to 30 characters, is a letter supplied or an abbreviation expanded by the editor.
8. **Remove points and cantillation.**
9. **Split into words, keeping the bracket state across words:**
   - a word that touches a gap is partial, so it becomes a break;
   - a word containing Latin letters or digits (labels, folio numbers, accounts) becomes a break;
   - a word with a restored letter becomes a break in strict but is kept in full;
   - expanded letters are removed in strict.

### Structure

- **Princeton:** the HTML gives blocks (`<h3>`) and lines (`<li>`), plus a language tag (`lang="he|jrb|ar|arc"`). Block labels are mapped to `recto / verso / margin / address / main / other`.
- **FGP:**
  - Line breaks are used when present.
  - **Genuzot** (Talmud) rows contain a marker such as `מסכת שבת (,,)` at every line. The text is split on it, and the header before the first marker is removed.
  - **Milikowsky:** everything before the first standalone `r`/`v` (title, edition note) is removed.
- **Position in the text** is computed within each block when line breaks are known:
  - `start` = the first 15% of lines (at least 2);
  - `end` = the last 15%;
  - otherwise `middle`;
  - `unknown` when there are no line breaks or the block has fewer than 3 lines.

### Output

`corpus_lines.parquet`, 697,688 lines. The columns are listed in [transcription_conventions.md](transcription_conventions.md) section 6.

## 5. Phrase counts (`phrases.py`)

Everything is done in DuckDB:

1. Copy the lines into a table `lines` with a running `id`.
2. Split each line's strict and full text on `‖` into segments, and each segment into a word list.
3. Generate every n-gram for n = 2..7 inside each segment, with its fragment (`src:doc`), genre domain and position. That is 144 million occurrences.
4. Keep phrases found in **at least 3 distinct fragments** (`MIN = 3`), separately for each layer.
5. Count **distinct fragments, not occurrences**, so one long text can't dominate. Counts are stored:
   - overall (`phrase.frags`);
   - by genre domain (`phrase_genre`);
   - by position (`phrase_pos`);
   - by genre × position (`phrase_dim`).

   Each table holds exact distinct counts. Adding up rows of `phrase_dim` would count a fragment twice when the phrase appears in two positions, which is why there are separate tables.

| Table | Rows | Columns |
|---|---|---|
| `phrase` | 7.1 M (3.7 M distinct phrases, counted per layer) | `pid, layer, n, phrase, frags, w1` (first word, indexed) |
| `phrase_dim` | 12.7 M | `pid, genre_domain, position, frags` |
| `phrase_genre`, `phrase_pos` | | the same, along one dimension |
| `lines` | 697,688 | the cleaned lines with their metadata |

The build takes about 3 minutes on the server with 64 threads. The database is 1.1 GB.

## 6. Static data files (`export_static.py`)

The online version can't run a database, so the database is turned into small gzip files that the browser fetches only when needed. GitHub Pages serves them as-is, and the page decompresses them with `DecompressionStream`.

| Files | Size | Content |
|---|---|---|
| `data/meta.json` | | genres (index → name), the partition table, the number of word buckets and lines per chunk, totals, build date |
| `data/p/NNNN.tsv.gz` | 642 files, 47 MB | phrases, partitioned by their leading characters |
| `data/w/NNNN.tsv.gz` | 1,024 files, 21 MB | word index: each word → the ids of the lines that contain it |
| `data/l/NNNN.json.gz` | 698 files, 59 MB | the lines, 1,000 per file, in id order |

No file is larger than about 850 KB. The total is 129 MB.

### Phrase files

The partition is chosen so that no file has more than 60,000 phrases. It starts with the first character of the phrase and adds characters (up to 6) until each group is small enough. `meta.parts` maps each key (for example `ו`, `של`, `אל`) to a file name.

Each row has six tab-separated fields:

```
phrase \t n \t fragments_strict \t fragments_full \t breakdown_strict \t breakdown_full
```

A breakdown is three lists separated by `|`:

```
<genre><pos><count>,...  |  <genre>.<count>,...  |  <pos><count>,...
   genre × position          by genre               by position
```

- `genre` is the index into `meta.genres`.
- `pos` is `s`, `m`, `e` or `u` (start, middle, end, unknown).
- `breakdown_full` is `=` when it is identical to strict.
- A count of 0 in one layer means the phrase is below 3 fragments in that layer.

### Word index

- **Bucket:** FNV-1a 32-bit hash of the word (over Unicode code points), modulo 1,024. The JavaScript `fnv()` reproduces the Python hash exactly.
- **Row format:** `word \t d1,d2,...`. The line ids are delta-coded in base 36.
- Words are indexed from the union of the strict and full text.

### Line chunks

A JSON array per line:

```
[shelfmark, library, genre_index, genre, block_kind, line_no, n_lines, pos, src, doc, mms, strict, full, raw]
```

`full` is `""` when it equals `strict`. `raw` is the transcription as the editor wrote it.

## 7. Search

### Pattern syntax and translation to a regular expression

The query is split into words. Each word becomes a regular-expression fragment:

| Input | Regex | Meaning |
|---|---|---|
| letter | the letter (escaped) | itself |
| `?` | `[א-ת]` | one unknown letter |
| `*` | `[^ ]*` | any letters inside the word |
| `_` | `[^ ]+` | one whole unknown word |
| letter with "look-alike letters" on | its class, e.g. `[דרך]` | the classes are ד/ר/ך, ה/ח/ת, ו/י/ן/ז, ב/כ, ס/ם, ג/נ, ע/צ, מ/ט |
| last word with "complete the last word" on | fragment + `[^ ]*` | the last word may continue: `נקול נ` finds `נקול נחן` |

The words are joined with single spaces. "Starts with" anchors the regex at the start of the phrase (`^…( |$)`); "Contains" anchors it at a word boundary anywhere (`(^| )…( |$)`). A trailing space in the query turns partial completion off for that query, so the last word must be whole.

### Finding phrases in the browser (`ENG.search` in `index.html`)

1. **Choose the partitions to load.**
   - With "Starts with" and a literal beginning (the characters before the first wildcard), only partitions whose key is a prefix of that beginning, or starts with it, are loaded. For a typical query that is one to three files.
   - With look-alike letters, every partition whose first letter is in the class is loaded.
   - With "Contains", or a pattern starting with a wildcard, all 642 files are loaded (about 47 MB). They are fetched 6 at a time, with progress shown, and kept in memory.
2. **Test the regex** against the phrase part of every row.
3. **Keep a phrase** if its length is within the chosen word range and at least the number of words typed, and its count in the selected layer is above zero.
4. **Read the count for the filters from the breakdown:**
   - genre and position → the genre × position list;
   - genre only → the genre list;
   - position only → the position list;
   - no filter → the total.
5. **Sort** by fragment count, then by length, and show the top 80.

### Where a phrase appears (`ENG.where`)

This loads the partition of the exact phrase and reads its genre × position list.

### Example lines (`ENG.examples`)

1. Fetch the word-index bucket for every distinct word of the phrase, and decode their line-id lists.
2. Intersect the lists, starting from the shortest. The result is the lines that contain **all** the words. This number is shown as "checking N lines with all these words".
3. Put the candidates in a fixed pseudo-random order: ids are multiplied by 2654435761 and sorted on the result. This gives a varied sample instead of the first texts in id order, and the order is stable.
4. Go through the candidates, fetching line chunks as needed (at most 40 new chunks per click).
5. Check each line: the exact phrase with word boundaries (`(^| |‖)phrase( |‖|$)`) in the selected layer, plus the genre and position filters.
6. Return 12 lines per click. "Show more lines" continues from where it stopped.

Very long lines (over 70 words, mostly Friedberg texts that lost their line breaks) are shown as a window of 25 words on each side of the match.

### Local app (`local-app/`)

`search.py` does the same matching in SQL over `phrases.duckdb`, using `regexp_matches`. When the query starts with a literal whole word, it uses the index on `w1`. The example count there is exact, because `examples()` counts every matching line.

`app.py` serves the page and four JSON endpoints:

- `/api/meta`
- `/api/search?q=&mode=&genre=&position=&layer=&alike=&partial=&n=2-7&limit=`
- `/api/where?phrase=&layer=`
- `/api/examples?phrase=&genre=&position=&layer=&k=&offset=`

Queries are serialized with a lock. Each query takes well under a second, and sharing one DuckDB connection across threads stalled.

### Measured speed

| Case | Time |
|---|---|
| Local app, typical query | 0.02–0.8 s |
| Online, "Starts with" | under 1 s after the first file loads |
| Online, "Contains" on a fresh visit | under 10 s locally, while all phrase files load once |

## 8. Rebuilding

On the Haifa server, in `/nas/archive/haifa-data/noam/fgp_report/`, with the virtual environment `venv` (pandas, pyarrow, duckdb, pymssql):

```bash
cd /nas/archive/haifa-data/noam/fgp_report
# 1. only if the FIST backup changed: start SQL Server, export the Friedberg transcriptions
../mssql/run_mssql.sh &                        # rootless SQL Server on 127.0.0.1:14333
venv/bin/python extract_fgp.py
pkill -u $USER sqlservr
# 2. update the Princeton texts
git -C pgp/pgp-text pull
# 3. clean, count, export (about 2 + 3 + 4 minutes)
venv/bin/python corpus.py
venv/bin/python phrases.py
venv/bin/python export_static.py               # -> phrase_site/data/
```

Then replace `data/` in this repository with `phrase_site/data/` and push. GitHub Pages republishes within a minute or two.

The genre and the fragment links come from the dashboard table (`geniza_fragments_status.parquet`). Rebuild the dashboard first if its genre mapping changed.

### Running the local app

Copy `phrases.duckdb` to `local-app/data/`, then:

```bash
cd local-app && ./start.command
```

`start.command` creates `.venv` (with duckdb and pandas) on first use and opens http://localhost:8770. The database is not in this repository because of its size.

### Querying from Python

```python
import search as S                                  # local-app/search.py
con = S._con('data/phrases.duckdb')
S.search('נקול נ', partial=True, genre='Documents', position='start', con=con)
S.examples('נקול נחן אלשהוד', genre='Documents', k=10, con=con)
S.where_it_appears('שהדותא דהות באנפנא', con=con)
```

From the command line, for example:

```bash
python search.py "שהדות? ד?ות באנפ?א" --genre Documents --examples
```

## 9. Known limitations

- **Line position is known for:**
  - 98% of Princeton words;
  - 67% of Genuzot words;
  - 41% of other Friedberg words;
  - almost none of Milikowsky's and Shmidman's texts, which were flattened in the export.

  Their phrases still count, but under "line not known".
- **Some editor remarks without any marker remain in the text,** mostly in Milikowsky and Ginzei Qedem. An example is `נקודות מעל`, the editor describing dots above letters. They appear as rare phrases.
- **Some mark meanings are inferred from context:** `^`, `$`, `<…>` and `(x ){y` in some Friedberg projects. FGP's sigla files (`DecodingFiles`) were not available.
- **The online example count** is "lines containing all the words", an upper bound. The shown lines are checked for the exact phrase.
- **The genre** is the unified genre of the fragment record, not of the specific text block. For example, a letter written on the back of a literary text gets the record's genre.
- **Phrases found in fewer than 3 fragments are not stored.** Unique wordings won't appear.
