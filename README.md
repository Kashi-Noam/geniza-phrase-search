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

"Look-alike letters" also matches ד/ר/ך, ה/ח/ת, ו/י/ן/ז, ב/כ, ס/ם, ג/נ, ע/צ, מ/ט.

## How it works

The site is static. The browser loads compressed data files from `data/` only as needed:

- `p/`: phrases, split by their first letters;
- `w/`: a word index;
- `l/`: the lines themselves.

The files are built from the Haifa server pipeline (`corpus.py`, `phrases.py`, `export_static.py`).

The transcriptions belong to their editors and projects. Please credit the Friedberg Genizah Project and the Princeton Geniza Project, and do not use the data commercially.
