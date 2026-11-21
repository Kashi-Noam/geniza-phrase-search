"""phrases.duckdb -> static files for the online phrase search (GitHub Pages; the browser does the searching).
  data/meta.json         genres, partitions, totals
  data/p/<key>.tsv.gz    phrases whose text starts with <key>: phrase, n, frags strict, frags full, breakdown strict, breakdown full ('=' if same)
  data/w/<b>.tsv.gz      word -> ids of the lines that contain it (delta-coded, base 36); bucket = FNV-1a(word) % NB
  data/l/<c>.json.gz     lines c*CH .. c*CH+CH-1: shelfmark, library, genre domain, genre, block, line no, lines, position, src, doc, mms, strict, full ('' if same), raw
breakdown = 'g<pos>count,...|g.count,...|<pos>count,...' : fragments by genre x position, by genre, by position (pos s/m/e/u)"""
import duckdb, json, gzip, os, sys, shutil, collections, time
OUT = '/nas/archive/haifa-data/noam/fgp_report/'
SITE = OUT + 'phrase_site/data/'
NB, CH, MAXROWS = 1024, 1000, 60000
P = {'start': 's', 'middle': 'm', 'end': 'e', 'unknown': 'u'}
t0 = time.time()
shutil.rmtree(SITE, ignore_errors=True)
for d in 'pwl': os.makedirs(SITE + d)
con = duckdb.connect(OUT + 'phrases.duckdb', read_only=True)
con.execute("SET threads TO 48")
G = [r[0] for r in con.execute("SELECT genre_domain FROM lines GROUP BY 1 ORDER BY count(*) DESC").fetchall()]
GI = {g: i for i, g in enumerate(G)}
def gz(path, text):
    with gzip.open(path, 'wt', encoding='utf-8', compresslevel=9) as f: f.write(text)

# ---------------------------------------------------------------- phrases
def enc(cells, gen, pos):
    a = ','.join(f'{GI[g]}{P[p]}{c}' for g, p, c in (x.split('|') for x in (cells or '').split(',') if x))
    b = ','.join(f'{GI[g]}.{c}' for g, c in (x.split('|') for x in (gen or '').split(',') if x))
    c_ = ','.join(f'{P[p]}{c}' for p, c in (x.split('|') for x in (pos or '').split(',') if x))
    return f'{a}|{b}|{c_}'
con.execute("CREATE TEMP TABLE dc AS SELECT pid, string_agg(genre_domain || '|' || position || '|' || frags, ',') cells FROM phrase_dim GROUP BY pid")
con.execute("CREATE TEMP TABLE dg AS SELECT pid, string_agg(genre_domain || '|' || frags, ',') gen FROM phrase_genre GROUP BY pid")
con.execute("CREATE TEMP TABLE dp AS SELECT pid, string_agg(position || '|' || frags, ',') pos FROM phrase_pos GROUP BY pid")
for layer in ('strict', 'full'):
    con.execute(f"""CREATE TEMP TABLE agg_{layer} AS SELECT p.phrase, p.n, p.frags, dc.cells, dg.gen, dp.pos
      FROM phrase p LEFT JOIN dc USING (pid) LEFT JOIN dg USING (pid) LEFT JOIN dp USING (pid) WHERE p.layer = '{layer}'""")
print('aggregated', round(time.time() - t0), 's', flush=True)
df = con.execute("""SELECT coalesce(s.phrase, f.phrase) phrase, coalesce(s.n, f.n) n, coalesce(s.frags, 0) fs, coalesce(f.frags, 0) ff,
                           s.cells sc, s.gen sg, s.pos sp, f.cells fc, f.gen fg, f.pos fp
                    FROM agg_strict s FULL OUTER JOIN agg_full f USING (phrase)""").fetchdf()
print('phrases', len(df), round(time.time() - t0), 's', flush=True)
df['bs'] = [enc(a, b, c) if fs else '' for a, b, c, fs in zip(df.sc, df.sg, df.sp, df.fs)]
df['bf'] = [('=' if bf == bs and fs == ff else bf) if ff else '' for bs, bf, fs, ff in
            zip(df.bs, [enc(a, b, c) if ff else '' for a, b, c, ff in zip(df.fc, df.fg, df.fp, df.ff)], df.fs, df.ff)]
df = df.sort_values(['phrase']).reset_index(drop=True)
# partition by leading characters so that no file is too big
def parts(sub, k):
    out = {}
    for key, g in sub.groupby(sub.phrase.str.slice(0, k)):
        if len(g) > MAXROWS and k < 6 and g.phrase.str.len().min() > k: out.update(parts(g, k + 1))
        else: out[key] = g
    return out
PART = parts(df, 1)
pmeta = {}
for i, (key, g) in enumerate(sorted(PART.items())):
    name = f'{i:04d}'
    gz(f'{SITE}p/{name}.tsv.gz', '\n'.join(f'{a}\t{b}\t{c}\t{d}\t{e}\t{f}' for a, b, c, d, e, f in zip(g.phrase, g.n, g.fs, g.ff, g.bs, g.bf)))
    pmeta[key] = [name, len(g)]
print('phrase files', len(pmeta), round(time.time() - t0), 's', flush=True)

# ---------------------------------------------------------------- lines and word postings
L = con.execute("""SELECT id, shelfmark, library, genre_domain, genre, block_kind, line_no, n_lines, position, src, doc, mms_id, strict, "full", raw
                   FROM lines ORDER BY id""").fetchdf()
N = len(L)
post = collections.defaultdict(list)
for i, s, f in zip(range(N), L.strict, L.full):
    for w in set((s + ' ' + f).replace('‖', ' ').split()): post[w].append(i)
def fnv(w):
    h = 0x811c9dc5
    for ch in w: h = ((h ^ ord(ch)) * 0x01000193) & 0xffffffff
    return h
B = collections.defaultdict(list)
def b36(x):
    s = ''
    while True:
        x, r = divmod(x, 36); s = '0123456789abcdefghijklmnopqrstuvwxyz'[r] + s
        if not x: return s
for w, ids in post.items():
    prev, d = 0, []
    for x in ids: d.append(b36(x - prev)); prev = x
    B[fnv(w) % NB].append(f'{w}\t{",".join(d)}')
for b in range(NB): gz(f'{SITE}w/{b:04d}.tsv.gz', '\n'.join(B.get(b, [])))
print('words', len(post), round(time.time() - t0), 's', flush=True)
def s_(v): return '' if v is None or v != v else str(v)
for c in range(0, N, CH):
    chunk = []
    for r in L.iloc[c:c + CH].itertuples():
        full = '' if r.full == r.strict else r.full
        chunk.append([s_(r.shelfmark), s_(r.library), GI[r.genre_domain], s_(r.genre), s_(r.block_kind), int(r.line_no), int(r.n_lines), P[r.position],
                      r.src, s_(r.doc), s_(r.mms_id), r.strict, full, r.raw])
    gz(f'{SITE}l/{c // CH:04d}.json.gz', json.dumps(chunk, ensure_ascii=False, separators=(',', ':')))
meta = {'genres': G, 'parts': pmeta, 'nb': NB, 'chunk': CH, 'lines': N,
        'fragments': con.execute("SELECT count(DISTINCT src || doc) FROM lines").fetchone()[0], 'phrases': len(df),
        'phrases_strict': int((df.fs > 0).sum()), 'phrases_full': int((df.ff > 0).sum()), 'built': time.strftime('%d %b %Y')}
json.dump(meta, open(SITE + 'meta.json', 'w'), ensure_ascii=False)
tot = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(SITE) for f in fs)
big = max((os.path.getsize(os.path.join(dp, f)), f) for dp, _, fs in os.walk(SITE) for f in fs)
print('done', round(time.time() - t0), 's | total', tot // 2**20, 'MB | largest file', big[0] // 2**10, 'KB', big[1])
for d in 'pwl': print(d, sum(os.path.getsize(SITE + d + '/' + f) for f in os.listdir(SITE + d)) // 2**20, 'MB in', len(os.listdir(SITE + d)), 'files')
