"""Geniza phrase search: a small local web server over phrases.duckdb.
   .venv/bin/python app.py [--port 8770]   then open http://localhost:8770"""
import json, os, sys, argparse, urllib.parse, math, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import duckdb
import search as S

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = duckdb.connect(S.DB, read_only=True)
LOCK = threading.Lock()                       # one query at a time: each takes well under a second
GENRES = [r[0] for r in BASE.execute("SELECT genre_domain FROM lines GROUP BY 1 ORDER BY count(*) DESC").fetchall()]
META = {'genres': GENRES, 'lines': BASE.execute('SELECT count(*) FROM lines').fetchone()[0],
        'fragments': BASE.execute("SELECT count(DISTINCT src || doc) FROM lines").fetchone()[0],
        'phrases': BASE.execute('SELECT count(*) FROM phrase').fetchone()[0]}

def clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return None
    if hasattr(v, 'item'): return v.item()
    return v

def rows(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict('records')]

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, code, body, ctype):
        b = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b)))
        self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path in ('/', '/index.html'):
                return self.send(200, open(os.path.join(HERE, 'index.html'), 'rb').read(), 'text/html; charset=utf-8')
            if u.path.startswith('/api/'):
              with LOCK:
                con = BASE
                f = dict(genre=q.get('genre') or None, position=q.get('position') or None, layer=q.get('layer', 'strict'), alike=q.get('alike') == '1')
                if u.path == '/api/meta': out = META
                elif u.path == '/api/search':
                    lo, hi = (int(x) for x in q.get('n', '2-7').split('-'))
                    pat = q.get('q', '').strip()
                    out = {'rows': rows(S.search(pat, q.get('mode', 'start'), n=(lo, hi), limit=int(q.get('limit', 60)), con=con, partial=q.get('partial') == '1', **f))} if pat else {'rows': []}
                elif u.path == '/api/examples':
                    df = S.examples(q['phrase'], k=int(q.get('k', 12)), offset=int(q.get('offset', 0)), con=con, **f)
                    total = int(df.total.iloc[0]) if len(df) else 0
                    out = {'total': total, 'rows': rows(df.drop(columns=['total']))}
                elif u.path == '/api/where':
                    out = {'rows': rows(S.where_it_appears(q['phrase'], q.get('layer', 'strict'), con=con))}
                else: return self.send(404, '{}', 'application/json')
                return self.send(200, json.dumps(out, ensure_ascii=False), 'application/json; charset=utf-8')
            self.send(404, 'not found', 'text/plain')
        except Exception as e:
            self.send(400, json.dumps({'error': str(e)}, ensure_ascii=False), 'application/json; charset=utf-8')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=8770); ap.add_argument('--host', default='127.0.0.1')
    a = ap.parse_args()
    print(f"Geniza phrase search: {META['phrases']:,} phrases, {META['lines']:,} lines, {META['fragments']:,} fragments")
    print(f'open http://localhost:{a.port}', flush=True)
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()
