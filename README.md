# Geniza Phrase Search

**Open it:** https://kashi-noam.github.io/geniza-phrase-search/

This page searches common phrases in human transcriptions of Cairo Geniza fragments. It's meant to help readers decipher damaged or unclear words by seeing which formulae are common and where in a text they appear.

## Data

- **Princeton Geniza Project:** transcriptions from [princetongenizalab/pgp-text](https://github.com/princetongenizalab/pgp-text) (CC BY-NC 4.0).
- **Friedberg Genizah Project:** transcriptions from the FGP database, limited to those published on the FGP website.

| | Count |
|---|---|
| Phrases of 2–7 words found in at least 3 fragments | 3.7 M |
| Fragments | 27,462 |
| Transcription lines | 697,688 |

Counts are numbers of fragments, not occurrences.

The transcriptions were cleaned into two versions:

- **Legible text only:** without the editors' restorations or expanded abbreviations.
- **With restorations:** with them.

Phrases never cross a gap or an illegible passage.

Each fragment has a genre, taken from a unified genre field that combines FGP, PGP and NLI catalogue tags. Each line has a position in its text (start, middle or end) wherever the line breaks are known.

## Search

| Type | Meaning | Example |
|---|---|---|
| `?` | one letter you can't read | `שהדות? ד?ות באנפ?א` |
| `*` | any letters | `ושלום*` |
| `_` | a whole word you can't read | `ברוך _ אלהינו` |
| last word | can be the beginning of a word; end the query with a space to ask for the whole word | `נקול נ` → `נקול נחן…` |

"Look-alike letters" also matches ד/ר/ך, ה/ח/ת, ו/י/ן/ז, ב/כ, ס/ם, ג/נ, ע/צ, מ/ט.

## How it works

The site is static. The browser loads compressed data files from `data/` only as needed and does the matching itself.

The full technical explanation is in [docs/TECHNICAL.md](docs/TECHNICAL.md): the pipeline, the cleaning, the counting, the data formats, the search algorithm and how to rebuild. How each transcription convention was cleaned is in [docs/transcription_conventions.md](docs/transcription_conventions.md).

| Folder | What it is |
|---|---|
| `index.html`, `data/` | The online site (GitHub Pages) |
| `pipeline/` | The scripts that build the data on the Haifa server: `extract_fgp.py` → `corpus.py` → `phrases.py` → `export_static.py`, plus `pgp_links.py` for the Princeton links |
| `local-app/` | A version that runs on your own computer: a Python server over the DuckDB database, with exact counts |
| `docs/` | Technical documentation |

The transcriptions belong to their editors and projects. Please credit the Friedberg Genizah Project and the Princeton Geniza Project, and do not use the data commercially.
