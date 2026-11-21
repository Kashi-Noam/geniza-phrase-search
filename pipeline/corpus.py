"""Human Geniza transcriptions (PGP + FGP) -> corpus_lines.parquet: one row per line, cleaned into a strict and a full text.
strict = only what can be read on the fragment (no editorial restorations or expansions); full = with them.
Both use ' ‖ ' for breaks (lacuna, illegible, block change): phrases must not cross a break."""
import pandas as pd, re, glob, html, os, collections, sys
OUT = '/nas/archive/haifa-data/noam/fgp_report/'
PGP = OUT + 'pgp/pgp-text/'
BR = '‖'
HEB = r'א-ת'

# ---------------------------------------------------------------- line cleaner
PTS = re.compile(r'[֑-ֽֿׁ-ׂׄ-ׇ]')       # points & cantillation (maqaf handled apart)
LAC = re.compile(r'\[\[?[\s .…?֑-ׇ]*\]\]?|\.{2,}|…|(?:\.\s){2,}\.?|-{2,}|\|')   # lacunae, illegible, rules, column breaks
DEL = re.compile(r'⟦[^⟧]*⟧|\[\[[^\]]*[א-ת][^\]]*\]\]\]?|<del>.*?</del>')               # deleted by the scribe
NOTE = re.compile(r'\((?:[^()]*)\)')                                         # editor's notes, sic, glosses, references
VAR = re.compile(r'\(([^(){}]*) \)\{')                                       # Genuzos variant: (scribe ){corrected
TRIPLE = re.compile(rf'(^|\s)([{HEB}])\2\2+')                               # export damage: לללדונו -> לדונו
LABEL = re.compile(r'^\s*(?:העתקות|ציטטות|צד|טור|עמוד)\s+[א-ת]{1,2}\'?\s')
ARAB = re.compile(r'[؀-ۿ]')
REF = re.compile(r"\([א-ת]{1,5}'\s+[א-ת\"']{1,4}(?:\s+[א-ת\"']{1,4})?(?:\s*\))?")   # unclosed Bible references: (תה' פה יא
EDNOTE = re.compile(r'(?:(?:יש )?הערת גליון|הערות שורה|התוספת מצויה|ראה אוצר)(?:\s+\S+){0,12}')   # editor's notes typed into the text

def balance(s):
    """brackets with no partner mark the broken edge of the fragment: turn them into lacuna marks;
    a mirrored pair (']...[' inside one word) is a restoration written backwards: swap it back"""
    st, bad = [], []
    for i, ch in enumerate(s):
        if ch == '[': st.append(i)
        elif ch == ']':
            if st: st.pop()
            else: bad.append(i)
    bad = sorted(bad + st)
    if not bad: return s
    out, used = list(s), set()
    for a in bad:
        if a in used: continue
        b = next((k for k in bad if k > a and k not in used and s[a] == ']' and s[k] == '[' and ' ' not in s[a:k]), None)
        if b is not None: out[a], out[b] = '[', ']'; used |= {a, b}
        else: out[a] = '\x01'; used.add(a)
    return ''.join(out)

def clean_line(s, conv):
    """-> (strict, full, uncertain) for one line of transcription"""
    s = html.unescape(s).replace(' ', ' ').replace('׳', "'").replace('״', '"').replace('`', "'").replace('־', ' ')
    s = s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    if conv != 'pgp': s = TRIPLE.sub(r'\1\2', s)
    s = LABEL.sub(' ', s)
    s = VAR.sub('', s)                       # keep the corrected reading
    s = EDNOTE.sub(' ', REF.sub(' ', s))
    s = DEL.sub(' ', s)
    unc = bool(re.search(r'\?|\^', s))
    s = NOTE.sub(' ', s)
    s = LAC.sub('\x01', s)
    s = balance(s)
    s = re.sub(r'[(){}*!$^:;,·/\\=+#_~@]', '', s)
    s = re.sub(r'\?', '', s)
    # <...> inside a line: short = letters supplied or abbreviation expanded by the editor; long or unmatched = passage marks
    s = re.sub(r'<([^<>]{1,30})>', lambda m: '\x02' + m.group(1) + '\x03', s)
    s = s.replace('<', '').replace('>', '')
    s = PTS.sub('', s)
    strict, full = [], []
    rest = exp = mirror = False                                              # bracket state runs across the words of the line
    for tok in s.split():
        if '\x01' in tok or re.search(r'[A-Za-z0-9½¼¾⅛⅓⅔]', tok):           # lacuna (words touching it are partial), labels, numbers
            strict.append(BR); full.append(BR)
            rest = rest and '\x01' not in tok.split(']')[-1] if ']' in tok else rest
            continue
        st, fu = [], []
        for ch in tok:
            if ch == '[':
                if mirror: rest = mirror = False
                else: rest = True
                continue
            if ch == ']':
                if rest: rest = False
                else: rest = mirror = True                                   # ']' before '[' = mirrored brackets in RTL text
                continue
            if ch == '\x02': exp = True; continue
            if ch == '\x03': exp = False; continue
            fu.append(ch)
            if rest: st.append('\x04')                                      # restored letter: word unusable in strict
            elif not exp: st.append(ch)
        w_full = ''.join(fu).strip('.-').lstrip('"\'')
        w_st = ''.join(st).strip('.-').lstrip('"\'')
        if not re.search(rf'[{HEB}\u0600-\u06ff]', w_full): continue
        full.append(w_full)
        if '\x04' in w_st: strict.append(BR)
        elif w_st: strict.append(w_st)
    return tidy(strict), tidy(full), unc

def tidy(toks):
    out = []
    for t in toks:
        if t == BR and (not out or out[-1] == BR): continue
        out.append(t)
    while out and out[-1] == BR: out.pop()
    return ' '.join(out)

# ---------------------------------------------------------------- block names
def block_kind(lbl):
    l = (lbl or '').lower()
    if 'address' in l: return 'address'
    if 'margin' in l or 'diagonal' in l or 'perpendicular' in l: return 'margin'
    if 'verso' in l or 'page b' in l or l.strip() in ('b', 'd', 'v'): return 'verso'
    if 'recto' in l or 'page a' in l or l.strip() in ('a', 'c', 'r'): return 'recto'
    return 'main' if not l.strip() else 'other'

# ---------------------------------------------------------------- PGP
rows = []
LI = re.compile(r'<h3>(.*?)</h3>|<li[^>]*>(.*?)</li>|lang="([a-z-]+)"', re.S)
for f in sorted(glob.glob(PGP + '*/*/*_transcription.html')):
    m = re.match(r'PGPID(\d+)_s(\d+)_(.*)_transcription', os.path.basename(f))
    pid, src_id, editor = m.group(1), m.group(2), m.group(3).replace('-', ' ')
    t = open(f, encoding='utf-8').read()
    t = re.sub(r'<del>.*?</del>', ' ⟦⟧ ', t, flags=re.S)
    block, lang, bi, lines = '', 'he', 0, []
    for h3, li, lg in LI.findall(t):
        if lg: lang = lg; continue
        if h3: block = html.unescape(re.sub('<[^>]+>', '', h3)).strip(); bi += 1; continue
        lm = re.search(r'lang="([a-z-]+)"', li)
        txt = re.sub(r'<[^>]+>', ' ', li)
        lines.append((bi, block, lm.group(1) if lm else lang, txt))
    for (bi_, blk, lg, txt) in lines:
        rows.append(('pgp', pid, f'pgp{pid}_s{src_id}_{editor}', editor, 'pgp', bi_, blk, lg, txt, True))
print('pgp lines', len(rows), flush=True)

# ---------------------------------------------------------------- FGP
z = pd.read_parquet(OUT + 'ngram_fgp_raw.parquet')
z = z[z.Sigla != 'Documentation for Princeton documents']                    # duplicates of PGP: keep the PGP version
z = z[~z.ID.isin(pd.read_parquet(OUT + 'ngram_fgp_not_public.parquet').ID)]        # not on the public FGP website
GEN = re.compile(r'(?:מסכת\s+[^\s(]+(?:\s+[^\s(]+){0,2}\s+)?\(,,\)')
def conv_of(r):
    who = r.ResearcherNameEng if isinstance(r.ResearcherNameEng, str) else ''
    if who.startswith('Genuzos'): return 'genuzos'
    if who == 'Avi Shmidman': return 'shmidman'
    if who == 'Chaim Milikowsky': return 'milikowsky'
    return 'fgp'
nf = 0
for r in z.itertuples():
    conv = conv_of(r)
    t = html.unescape(r.FileTxt if isinstance(r.FileTxt, str) else '').replace('\r\n', '\n').replace('\r', '\n')
    if conv == 'genuzos' and '(,,)' in t:
        t = t[GEN.search(t).end():]                                            # drop the header before the first line marker
        parts = GEN.split(t)
    else:
        parts = t.split('\n')
    if conv == 'milikowsky':
        m = re.search(r'(?:^|\s)[rv](?=\s)', t)
        if m: t = t[m.end():]; parts = t.split('\n')
    parts = [p for p in parts if p.strip()]
    has = len(parts) > 1
    for p in parts:
        rows.append(('fgp', str(r.InventoryId), f'fgp{r.ID}', r.ResearcherNameEng, conv, 0, '', 'he', p, has)); nf += 1
print('fgp lines', nf, flush=True)

L = pd.DataFrame(rows, columns=['src', 'doc', 'tid', 'researcher', 'conv', 'block_no', 'block', 'lang', 'raw', 'has_lines'])
res = [clean_line(s, c) for s, c in zip(L.raw, L.conv)]
L['strict'] = [a for a, b, c in res]; L['full'] = [b for a, b, c in res]; L['uncertain'] = [c for a, b, c in res]
L = L[L.full.str.len() > 0].copy()
L['script'] = ['arabic' if ARAB.search(x) else 'hebrew' for x in L.full]
L['block_kind'] = L.block.map(block_kind)

# line positions within each block of each transcription (only where line breaks are known)
g = L.groupby(['tid', 'block_no'])
L['line_no'] = g.cumcount() + 1
L['n_lines'] = g.raw.transform('size')
L['line_from_end'] = L.n_lines - L.line_no + 1
def relpos(r):
    if not r.has_lines or r.n_lines < 3: return 'unknown'
    if r.line_no <= max(2, round(.15 * r.n_lines)): return 'start'
    if r.line_from_end <= max(2, round(.15 * r.n_lines)): return 'end'
    return 'middle'
L['position'] = [relpos(r) for r in L[['has_lines', 'n_lines', 'line_no', 'line_from_end']].itertuples()]

# ---------------------------------------------------------------- fragment metadata: MMS, shelfmark, genre
d = pd.read_parquet(OUT + 'geniza_fragments_status.parquet', columns=['mms_id', 'shelfmark_best', 'genre_domain', 'genre', 'pgp_ids', 'pgp_doc_types', 'fist_inventory_ids', 'library_best'])
def explode(col):
    x = d[d[col].notna()].assign(k=lambda y: y[col].astype(str).str.split(';')).explode('k')
    x['k'] = x.k.str.strip(); return x.drop_duplicates('k').set_index('k')
P, F = explode('pgp_ids'), explode('fist_inventory_ids')
meta = pd.concat([P.assign(src='pgp'), F.assign(src='fgp')]).reset_index().rename(columns={'k': 'doc'})
meta = meta[['src', 'doc', 'mms_id', 'shelfmark_best', 'library_best', 'genre_domain', 'genre', 'pgp_doc_types']]
L = L.merge(meta, on=['src', 'doc'], how='left')
L['genre_domain'] = L.genre_domain.fillna('(no genre)')
L['genre'] = L.genre.fillna('(no genre)')

COLS = ['src', 'doc', 'tid', 'mms_id', 'shelfmark_best', 'library_best', 'genre_domain', 'genre', 'pgp_doc_types', 'researcher', 'conv', 'lang', 'script',
        'block', 'block_kind', 'line_no', 'n_lines', 'line_from_end', 'position', 'has_lines', 'uncertain', 'raw', 'strict', 'full']
L[COLS].to_parquet(OUT + 'corpus_lines.parquet', index=False)

# ---------------------------------------------------------------- report
W = lambda s: s.str.replace(BR, ' ').str.split().str.len().sum()
print('\nlines', len(L), '| transcriptions', L.tid.nunique(), '| fragments', L.groupby('src').doc.nunique().to_dict())
for k, x in L.groupby('src'): print(f'{k}: words full {W(x.full):,}  strict {W(x.strict):,}  lines with position {(x.position != "unknown").mean():.0%}')
print('script', L.script.value_counts().to_dict())
print('genre domains (words, full):'); print(L.assign(w=L.full.str.split().str.len()).groupby('genre_domain').w.sum().sort_values(ascending=False).to_string())
print('no fragment metadata (lines):', L.mms_id.isna().sum())
