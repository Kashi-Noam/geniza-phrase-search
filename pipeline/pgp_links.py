"""Shelfmarks in the corpus -> Princeton Geniza Project documents, so that every line can link to the PGP website.
  python pgp_links.py <fragments.csv> <phrases.duckdb> <out.json>
fragments.csv is data/fragments.csv of https://github.com/princetongenizalab/pgp-metadata (shelfmark -> pgpids).
Out: {"our shelfmark": ["PGP shelfmark", "pgpid,pgpid,..."]}, only for shelfmarks found in the PGP.
FIST and PGP write shelfmarks differently ('T-S 13 J 3.27' / 'T-S 13J3.27', 'heb. f. 101.30' / 'Bodl. MS heb. f 101/30'),
so both sides are compared after norm(). Lines transcribed by the PGP link to their own document id instead (see index.html)."""
import csv, json, re, sys, duckdb

def norm(s):
    s = str(s).lower()
    if ':' in s: s = re.sub(r'^[^:]*:\s*:?\s*', '', s)                 # 'CUL: : T-S AS 103.277', 'Manchester: B 3402'
    s = re.sub(r'^(bodl\.?\s*)?(ms\.?\s*)?heb\.?', 'heb', s)           # Bodleian
    s = re.sub(r'^(jrl|bl)\s+', '', s)                                  # John Rylands, British Library
    s = re.sub(r'\s+', '', s.replace('/', '.'))                         # 'heb. f 101/30' = 'heb. f. 101.30'
    return re.sub(r'\.(?!(?<=\d\.)\d)', '', s)                         # drop dots, except between digits: 1.15 and 11/5 stay apart

frag_csv, db, out = sys.argv[1:4]
idx = {}
with open(frag_csv, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        idx.setdefault(norm(r['shelfmark']), (r['shelfmark'], r['pgpids'].replace(';', ',').replace(' ', '')))
ours = [r[0] for r in duckdb.connect(db, read_only=True).execute("SELECT DISTINCT shelfmark FROM lines WHERE shelfmark IS NOT NULL").fetchall()]
links = {s: list(idx[norm(s)]) for s in ours if norm(s) in idx}
json.dump(links, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'{len(links)} of {len(ours)} shelfmarks found in the PGP -> {out}')
