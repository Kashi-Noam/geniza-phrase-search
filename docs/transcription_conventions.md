# Geniza phrase search: transcription sources, markup and cleaning rules

Step 1 of the phrase-search plan: what the human transcriptions look like, and how to clean them.
Surveyed 21 Nov 2026 on the full PGP repository and the full FGP export.

## 1. Sources

| | PGP (Princeton) | FGP (Friedberg) |
|---|---|---|
| Where | github.com/princetongenizalab/pgp-text (commit f941a5b, 10 Nov 2026) | FIST backup, table `dbo.zzTransForRosetta` (the export prepared for NLI Rosetta) |
| Transcriptions | 8,524 files | 51,922 transcriptions (+4,808 translations, skipped) |
| Fragments | ~8,500 documents (PGPID) | 23,319 inventories |
| Words | 2.3 M | 18.8 M |
| Line breaks | yes: every line is an `<li>` in the HTML version | only 15% of rows (5.7 M words); the rest were flattened to one line by the export |
| Text blocks | yes: `<h3>` labels (Recto, Verso, right margin, address...) | no |
| Language tag | yes: `lang="he"`, `jrb` (Judeo-Arabic), `ar`, `arc`, `lad` per block | one field, mostly empty |
| Conventions | one project style, fairly consistent | ~36 different "sigla" legends, one per project or researcher |

Two smaller FGP sources were checked and are **not** the main corpus:

- `FGP/FGP_Geniza_transcriptions/alto/`: 7,664 page files with lines aligned to the images, mostly Talmud and Mishneh Torah. The markup was already stripped (dots for illegible letters, no brackets). It is useful later for word-on-image links, but it is too small to be the corpus.
- `dbo.UnitTranscription` only points to files that are not on the server.

**Overlap:** 4,714 FGP rows come from Princeton ("Documentation for Princeton documents": Goitein's typed texts, Gil, Cohen, Friedman...). They duplicate PGP, so drop them and keep the PGP version, which has lines and blocks.

**Who dominates FGP:** "Genuzos 1" is 26,693 rows and 7.5 M words, i.e. 40% of all FGP words. These are Bavli manuscripts from the Genuzot project. Without a genre filter the Talmud will dominate the counts. Next come Milikowsky (2.1 M words, midrash), Glick (1.0 M, responsa) and Ginzei Qedem (0.6 M).

## 2. Markup found, and what each mark means

Meanings are inferred from context, project by project. Most of the FGP legend files (`CODE.Legend`, folder `DecodingFiles`) are not on the server. Asking FGP for them would settle the doubtful rows.

### Shared by almost everyone

| Mark | Meaning | Count | Rule |
|---|---|---|---|
| `[א]`, `[פי]` | letters restored by the editor | PGP 6,782 files; FGP 30,604 rows | keep in the *full* text, mark as restored; remove from the *strict* text |
| `[ ]`, `[...]`, `[ ... ]` | lacuna (gap) of unknown length | very common | **break**: no phrase may cross it |
| `...`, `....`, `. . .` | illegible letters or words | PGP 2,370 files; FGP 34,842 rows | break; a word with dots inside it (`קר א כי תצ....`) is dropped |
| `?` alone, `(?)` | uncertain reading | PGP 2,107; FGP 27,640 | keep the word; flag the phrase as "uncertain" |
| `(!)` | sic: written like that | PGP | remove the mark, keep the word as written |
| `'` / `׳`, `"` / `״` | abbreviation, number | everywhere | keep as part of the token (ר', ע"ה, אלקנט'); unify ׳→' and ״→" |
| vowel points and cantillation | | PGP 513 files; FGP 5,779 rows (Shmidman: all) | remove for matching (keep the original for display) |

### PGP-specific

| Mark | Meaning | Rule |
|---|---|---|
| `⟦מחן⟧` (307 files), `<del>` in HTML | deleted by the scribe | *strict* = text as the scribe left it, so remove |
| `{ובו הייתי}` (321 files) | added above the line by the scribe | keep, in place |
| `(=נסתטיע)`, `(אלסגון ?)` | editor's correction or gloss | remove |
| `<מ>` (single letters) | letter added by the editor | remove in strict, keep in full |
| `< ... >` over many lines | a whole passage set apart (another hand, or a later addition) | keep the text, drop the marks |
| `[[א]]` | doubtful restoration | treat like `[ ]` |
| `Recto`, `verso`, `margin`, `page b`, `top of page` | block labels (also in the HTML `<h3>`) | remove from the text; use as the block name |
| Arabic script (1,656 files, 1,316 blocks `lang="ar"`) | documents in Arabic script | separate layer; never mix with Hebrew-script phrases |
| `½ ¼ ⅛`, digits | accounts | drop |

### FGP: depends on the project (decided by the `Sigla` field and the researcher)

| Mark | Who | Meaning | Rule |
|---|---|---|---|
| `מסכת שבת (,,)` repeated every ~18 words | Genuzos 1 (61% of its rows) | line marker inserted by the export | **use it to restore line breaks**, then remove |
| first line: `לח ב עד לז ב מ שבת MSS ... friedberg ...` | Genuzos 1 | header: folio range, tractate, library | remove (everything before the first marker) |
| `?ב?ל`, `כ?דא?מרן` | Genuzos 1 | letters between `?` are doubtful | keep the letters, drop `?`, flag as uncertain |
| `(ג ){ט` | Genuzos 1 | variant: scribe wrote ג, corrected to ט | keep the corrected reading |
| `[[נמי]]` | Genuzos 1, Goitein | deleted or crossed-out text | strict = remove |
| `ב<רוך>`, `אלהי<נו מלך העולם>` | Avi Shmidman (92% of rows) | **abbreviation expanded by the editor** | strict = remove the expansion (keep `ב`); full = expand |
| `<י>` inside words | Maman, Glick | letter supplied by the editor | same as above |
| `ד^פ^ס^ק^`, `של^ו` | Glick, Eliyahu, Milikowsky | `^` after a letter = doubtful letter | drop `^`, flag as uncertain |
| `ה$ק$ב$ה$`, `ת$ני` | Milikowsky (91% of rows) | `$` after a letter = mark above the letter (abbreviation stroke) | drop `$` |
| `$י$` | some FGP rows | special letter mark | drop `$` |
| `//אללה /` | Goitein's typed texts | interlinear addition | keep the text, drop the marks |
| `|` | Goitein's typed texts | line or column break | break |
| `` דר` `` | Gil | abbreviation mark | treat like `'` |
| `*סליק פירקא*`, `*הדרן עלך...*` | Genuzos | chapter-end formula, marked by the editor | keep the words, drop `*` (they are real text and real formulae) |
| `{ ... }` with `[[[` | Glick | messy nested additions | keep the text, drop the marks |
| headings in Latin script (`Cambridge University Library Taylor Schechter...`, `FRIDBERG GENIZA PROJECT Collected by...`, `T S NS`, `r`, `v`) | Milikowsky, Maman, Ginzei Qedem, Cowley | header and side labels | remove Latin-script tokens and the header line |
| `(מהד' הורוביץ עמ' / – /)`, `(תהל...)` | Genuzos, Eliyahu, Sklare | edition or Bible reference by the editor | remove |
| `העתקות א`, `ציטטות ב`, `צד א'` | Eliyahu, Glick | section labels by the editor | remove |

### Export damage in FGP (to repair, not to interpret)

- **Tripled prefix letters:** `לללדונו`, `וווהמקראות`, `מממטומאת`, `בבבדידיה`, also `JJJTS`, `SSS`. No Hebrew word starts with the same letter three times, so collapse to one letter.
  - Shmuel Glick: 49 per 1,000 words
  - Aharon Maman: 17 per 1,000 words
  - Moshe Gil: 10 per 1,000 words
  - Mark Cohen: 5 per 1,000 words
- **Mirrored brackets** in right-to-left text: `)?? מן`, `(? מן`, `יתל]וה[`. Seen in Sklare's rows (32% contain `(? `) and in a few others. Flip a bracket that opens to the left of a Hebrew word.
- **Line breaks:**
  - 85% of rows have none.
  - For Genuzos they can be restored from the `(,,)` markers.
  - For the rest, line position is unknown. Those rows still count for phrases, but not for the "start / end of text" filter.
- HTML entities such as `&#x0D;` (line break): decode them.

## 3. The cleaning pipeline

For each transcription:

1. **Pick the parser by source and convention:** PGP; FGP by its `Sigla` value or researcher (Genuzos, Shmidman, Milikowsky, Glick, Goitein-style, generic). Skip FGP rows that duplicate PGP.
2. **Repair export damage:** entities, tripled prefixes, mirrored brackets.
3. **Restore structure:**
   - PGP lines and blocks from the HTML;
   - Genuzos lines from `(,,)`;
   - other FGP lines from the line breaks when present.
   - Remove headers, block labels, Latin script and references.
4. **Tokenize** each line into words. Every token carries flags: `restored` (inside `[ ]`), `expanded` (`<...>` in Shmidman/Maman), `uncertain` (`?`, `^`), `deleted` (`⟦ ⟧`, `[[ ]]`).
5. Produce two token streams per line:
   - **strict**: what the scribe left that can be read. No restored or expanded letters; a word with any restored letter is dropped.
   - **full**: restorations and expansions included, deletions removed.
6. **Breaks:** a lacuna, illegible dots, `|` or a block change ends the phrase window. N-grams never cross a break.
7. **Normalize for matching only:** remove points, unify `׳ ״` and quote characters, collapse whitespace. Keep final letters and spelling (plene/defective) as written.
8. **Store one row per line:**
   - source, fragment id (MMS, PGPID, FGP inventory), shelfmark;
   - genre domain and genre (from the dashboard table), language/script;
   - block (recto, verso, margin, address), line number from the start and from the end, relative position (start / middle / end, or unknown);
   - strict text, full text, uncertain flag, researcher.

## 4. What this gives the phrase search

- About 16 M usable words after removing duplicates and headers: 2.3 M PGP plus about 14 M FGP. Talmud is about half of FGP, so the genre filter is essential.
- **Line position:**
  - known for all PGP;
  - known for Genuzos (Talmud) via the markers;
  - known for 15% of other FGP rows;
  - so the "start of the text" filter will lean mostly on PGP documents. That suits your use case: legal deeds and letters are mostly PGP.
- Each phrase is counted in strict and full text, in number of fragments, so one long text doesn't dominate.

## 5. Open questions

1. Ask FGP for the sigla legends (`DecodingFiles`, 36 files) to confirm the meaning of `^`, `$`, `<...>` and `(x ){y`. The rules above are inferred from context.
2. Usage terms: FGP stores copyright per transcription (`HebCopyRight` / `EngCopyRight`). The PGP data is CC BY-NC 4.0. The public site shows full lines from both projects, with permission, and credits both. FGP transcriptions that are not on the public FGP website (27) are excluded.

## 6. Step 2 result: the cleaned line corpus (21 Nov 2026)

- **File:** `/nas/archive/haifa-data/noam/fgp_report/corpus_lines.parquet` (190 MB), built by `corpus.py` in the same folder. Figures below are from the first build; after removing 27 non-public FGP transcriptions the totals are 697,688 lines and 27,462 fragments.
- **Size:** 697,695 lines from 55,626 transcriptions of 27,468 fragments (19,727 FGP, 7,741 PGP).

| | Words, full | Words, strict | Words with known line position |
|---|---|---|---|
| PGP | 1.92 M | 1.87 M | 98% |
| FGP | 14.16 M | 13.23 M | Genuzot 67%, other FGP 41%, Milikowsky 8%, Shmidman 1% |
| Documents (both sources) | 2.55 M | | 74% |

**Columns:**
- `src`, `doc` (PGPID or FGP inventory), `tid` (transcription), `mms_id`, `shelfmark_best`, `library_best`
- `genre_domain`, `genre`, `pgp_doc_types`, `researcher`, `conv` (which cleaning rules were used)
- `lang`, `script`
- `block`, `block_kind` (recto, verso, margin, address, main), `line_no`, `n_lines`, `line_from_end`
- `position` (start = first 15% of lines, end, middle, unknown), `has_lines`, `uncertain`
- `raw`, `strict`, `full`: breaks are written as ‖, and phrases must not cross them.

**Fixes made after checking samples:**
- a lone `[` or `]` at a broken edge is a lacuna, not a restoration;
- lacunae filled with dagesh dots `[ּ ּ ּ]` are gaps;
- `@` marks in Genuzot are removed;
- unclosed Bible references `(תה' פה יא` are removed;
- Milikowsky's header (everything before the first `r`/`v`) is removed;
- editor notes typed into the text ("הערות שורה", "יש הערת גליון", "ראה אוצר") are removed, up to 12 words each.

**Known leftovers:** some editor remarks without a marker remain, mostly in Milikowsky and Ginzei Qedem. 3,876 lines have no link to a fragment record.

**Review sample:** `corpus_sample.csv`, 250 random lines showing raw, strict and full side by side.

## 7. Step 3 result: phrase counts and pattern search (21 Nov 2026)

- **Database:** `/nas/archive/haifa-data/noam/fgp_report/phrases.duckdb` (1.1 GB), built by `phrases.py` in about 3 minutes.
  - 7.1 M phrases of 2–7 words that occur in at least 3 fragments: 3.7 M in the full text, 3.4 M in the strict text.
  - Counts are of fragments, not occurrences. Each phrase is counted overall, by genre domain, by position, and by both.
  - The cleaned lines are in the same file, for example lines.
- **Search:** `search.py` in the same folder.
  - `search()` returns the phrases that match.
  - `examples()` returns real lines with the shelfmark, the line number and an NLI or PGP link.
  - `where_it_appears()` returns the genre and position breakdown of one phrase.
  - Typical query time is 0.02–0.5 s.
- **Pattern syntax:** `?` one unknown letter; `*` any letters; `_` a whole unknown word. The look-alike option also matches ד/ר/ך, ה/ח/ת, ו/י/ן/ז, ב/כ, ס/ם, ג/נ, ע/צ, מ/ט.
- **From the server shell:**
  `venv/bin/python search.py "שהדות? ד?ות באנפ?א" --genre Documents --examples`
  Options: `--mode contains`, `--position start|middle|end`, `--layer full`, `--alike`, `--n 3-5`.
