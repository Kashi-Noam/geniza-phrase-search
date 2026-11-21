"""Phrase search over phrases.duckdb.

Pattern syntax (one or more words, separated by spaces):
  ?      one letter you cannot read          כאן נ?ן
  *      any number of letters (0 or more)   בית דין אל*
  _      a whole word you cannot read        כאן _ בית
  look_alike=True also matches letters that look alike in Geniza scripts (ד/ר/ך, ה/ח/ת, ו/י/ן/ז, ב/כ, ס/ם, ג/נ, ע/צ, מ/ט)

  partial=True: the last word may be the beginning of a word (נקול נ finds נקול נחנא)

  python search.py "כאן נ?ן" [--partial] [--mode start|contains] [--genre Documents] [--position start] [--layer strict|full] [--alike] [--n 3-5] [--examples]
"""
import duckdb, re, sys, os, argparse
DB = os.environ.get('PHRASES_DB') or next((p for p in [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'phrases.duckdb'),
      '/nas/archive/haifa-data/noam/fgp_report/phrases.duckdb'] if os.path.exists(p)), 'phrases.duckdb')
HEB = 'א-ת'
ALIKE = ['דרך', 'החת', 'ויןז', 'בכ', 'סם', 'גנ', 'עצ', 'מט']
CLS = {ch: g for g in ALIKE for ch in g}

def word_rx(w, alike):
    if w == '_': return f"[^ ]+"
    out = ''
    for ch in w:
        if ch == '?': out += f'[{HEB}]'
        elif ch == '*': out += f'[^ ]*'
        elif alike and ch in CLS: out += f'[{CLS[ch]}]'
        else: out += re.escape(ch)
    return out

def to_regex(pattern, mode, alike, partial=False):
    words = pattern.split()
    body = ' '.join(word_rx(w, alike) + ('[^ ]*' if partial and i == len(words) - 1 and w != '_' else '')   # partial: the last word may continue
                    for i, w in enumerate(words))
    return ('^' if mode == 'start' else '(^| )') + body + '( |$)', words

def _con(db):
    return duckdb.connect(db or DB, read_only=True)

def search(pattern, mode='start', genre=None, position=None, layer='strict', alike=False, n=(2, 7), limit=40, con=None, db=None, partial=False):
    """phrases matching the pattern, most fragments first. genre/position may be a string or a list."""
    con = con or _con(db)
    rx, words = to_regex(pattern, mode, alike, partial)
    where, args = ["p.layer = ?", "p.n BETWEEN ? AND ?", "regexp_matches(p.phrase, ?)"], [layer, max(n[0], len(words)), n[1], rx]
    w0 = words[0]
    if mode == 'start' and not alike and not (partial and len(words) == 1) and re.fullmatch(f'[{HEB}\'"]+', w0):   # literal first word: use the index
        where.append("p.w1 = ?"); args.append(w0)
    dims = []
    for col, val in (('genre_domain', genre), ('position', position)):
        if val:
            val = [val] if isinstance(val, str) else list(val)
            dims.append(f"d.{col} IN ({','.join('?' * len(val))})"); args += val
    # exact distinct-fragment table for the filters used (several values of one filter are summed, so may count a fragment twice)
    tbl = 'phrase_dim' if genre and position else 'phrase_genre' if genre else 'phrase_pos'
    if dims:
        q = f"""SELECT p.phrase, p.n, sum(d.frags) AS frags, any_value(p.frags) AS frags_all
                FROM phrase p JOIN {tbl} d USING (pid) WHERE {' AND '.join(where + dims)}
                GROUP BY p.phrase, p.n ORDER BY frags DESC, p.n DESC LIMIT {int(limit)}"""
    else:
        q = f"""SELECT p.phrase, p.n, p.frags, p.frags AS frags_all FROM phrase p WHERE {' AND '.join(where)}
                ORDER BY p.frags DESC, p.n DESC LIMIT {int(limit)}"""
    return con.execute(q, args).fetchdf()

def examples(phrase_or_pattern, genre=None, position=None, layer='strict', alike=False, k=10, offset=0, con=None, db=None):
    """real lines that contain it, with shelfmark, line number and a link to the NLI record"""
    con = con or _con(db)
    rx, _ = to_regex(phrase_or_pattern, 'contains', alike)
    rx = rx.replace('(^| )', '(^| |‖)').replace('( |$)', '( |‖|$)')
    col = 'strict' if layer == 'strict' else '"full"'
    where, args = [f"regexp_matches({col}, ?)"], [rx]
    for c, val in (('genre_domain', genre), ('position', position)):
        if val:
            val = [val] if isinstance(val, str) else list(val)
            where.append(f"{c} IN ({','.join('?' * len(val))})"); args += val
    q = f"""SELECT shelfmark, library, genre_domain, genre, block_kind, line_no, n_lines, position, raw, {col} AS text, src, doc, mms_id
            FROM lines WHERE {' AND '.join(where)} ORDER BY hash(id) LIMIT {int(k)} OFFSET {int(offset)}"""
    df = con.execute(q, args).fetchdf()
    df['total'] = con.execute(f"SELECT count(*) FROM lines WHERE {' AND '.join(where)}", args).fetchone()[0]
    df['link'] = [f'https://www.nli.org.il/he/manuscripts/NNL_ALEPH{m}/NLI' if isinstance(m, str) and m.isdigit()
                  else (f'https://geniza.princeton.edu/en/documents/{d}/' if s == 'pgp' else '') for m, d, s in zip(df.mms_id, df.doc, df.src)]
    return df

def where_it_appears(phrase, layer='strict', con=None, db=None):
    """for one exact phrase: fragments by genre domain and by position"""
    con = con or _con(db)
    return con.execute("""SELECT d.genre_domain, d.position, d.frags FROM phrase p JOIN phrase_dim d USING (pid)
                          WHERE p.layer = ? AND p.phrase = ? ORDER BY d.frags DESC""", [layer, phrase]).fetchdf()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('pattern'); ap.add_argument('--mode', default='start'); ap.add_argument('--genre'); ap.add_argument('--position')
    ap.add_argument('--layer', default='strict'); ap.add_argument('--alike', action='store_true'); ap.add_argument('--n', default='2-7')
    ap.add_argument('--partial', action='store_true', help='the last word may be the beginning of a word'); ap.add_argument('--limit', type=int, default=25); ap.add_argument('--examples', action='store_true'); ap.add_argument('--db')
    a = ap.parse_args(); lo, hi = map(int, a.n.split('-'))
    con = _con(a.db)
    r = search(a.pattern, a.mode, a.genre, a.position, a.layer, a.alike, (lo, hi), a.limit, con=con, partial=a.partial)
    print(r.to_string(index=False))
    if a.examples and len(r):
        e = examples(r.phrase.iloc[0], a.genre, a.position, a.layer, con=con, k=5)
        print('\nexamples of:', r.phrase.iloc[0])
        for x in e.itertuples(): print(f'  {x.shelfmark} (line {x.line_no}/{x.n_lines}, {x.position}, {x.genre_domain}): {x.text[:140]}  {x.link}')
