"""corpus_lines.parquet -> phrases.duckdb: every 2-7-word phrase that occurs in at least MIN fragments,
counted in fragments (not occurrences), by genre domain and by position in the text, for the strict and the full text.
Phrases never cross a break (‖)."""
import duckdb, os, sys, time
OUT = '/nas/archive/haifa-data/noam/fgp_report/'
DB = OUT + 'phrases.duckdb'
MIN = 3
t0 = time.time()
if os.path.exists(DB): os.remove(DB)
con = duckdb.connect(DB)
con.execute("SET threads TO 64; SET memory_limit='200GB'; SET preserve_insertion_order=false")
con.execute(f"SET temp_directory='{OUT}duck_tmp'")

con.execute(f"""CREATE TABLE lines AS
 SELECT row_number() OVER () AS id, src, doc, tid, mms_id, shelfmark_best AS shelfmark, library_best AS library, genre_domain, genre, pgp_doc_types,
        researcher, script, block, block_kind, line_no, n_lines, position, has_lines, uncertain, raw, strict, "full"
 FROM read_parquet('{OUT}corpus_lines.parquet')""")
print('lines', con.execute('SELECT count(*) FROM lines').fetchone()[0], round(time.time() - t0), 's', flush=True)

# word lists per break-free segment, for both layers
con.execute("""CREATE TEMP TABLE seg AS
 SELECT l.id, l.doc, l.src, l.genre_domain, l.position, s.layer, string_split(trim(s.seg), ' ') AS w
 FROM lines l, LATERAL (SELECT 'strict' AS layer, unnest(string_split(l.strict, '‖')) AS seg
                        UNION ALL SELECT 'full', unnest(string_split(l."full", '‖'))) s
 WHERE length(trim(s.seg)) > 0""")
con.execute("DELETE FROM seg WHERE len(w) < 2")
print('segments', con.execute('SELECT count(*) FROM seg').fetchone()[0], round(time.time() - t0), 's', flush=True)

# all n-grams with their fragment (source + doc id), genre and position
con.execute("""CREATE TEMP TABLE occ AS
 SELECT layer, n, array_to_string(w[i:i+n-1], ' ') AS phrase, src || ':' || doc AS frag, genre_domain, position
 FROM seg, range(2, 8) t(n), LATERAL (SELECT unnest(range(1, len(w) - n + 2)) AS i)
 WHERE len(w) >= n""")
print('occurrences', con.execute('SELECT count(*) FROM occ').fetchone()[0], round(time.time() - t0), 's', flush=True)

con.execute(f"""CREATE TABLE phrase AS
 SELECT row_number() OVER () AS pid, layer, n, phrase, frags, split_part(phrase, ' ', 1) AS w1 FROM (
   SELECT layer, n, phrase, count(DISTINCT frag) AS frags FROM occ GROUP BY ALL HAVING count(DISTINCT frag) >= {MIN})""")
print('phrases kept', con.execute('SELECT count(*) FROM phrase').fetchone()[0], round(time.time() - t0), 's', flush=True)

# breakdowns: distinct fragments by genre domain, by position, and by both (so counts are exact for one value of each filter)
con.execute("""CREATE TEMP TABLE po AS SELECT p.pid, o.frag, o.genre_domain, o.position FROM occ o JOIN phrase p USING (layer, n, phrase)""")
con.execute("CREATE TABLE phrase_dim AS SELECT pid, genre_domain, position, count(DISTINCT frag) AS frags FROM po GROUP BY ALL")
con.execute("CREATE TABLE phrase_genre AS SELECT pid, genre_domain, count(DISTINCT frag) AS frags FROM po GROUP BY ALL")
con.execute("CREATE TABLE phrase_pos AS SELECT pid, position, count(DISTINCT frag) AS frags FROM po GROUP BY ALL")
con.execute("DROP TABLE po; DROP TABLE occ; DROP TABLE seg")
con.execute("CREATE INDEX phrase_w1 ON phrase(layer, w1)")
print('dims', con.execute('SELECT count(*) FROM phrase_dim').fetchone()[0], round(time.time() - t0), 's', flush=True)
print(con.execute("SELECT layer, n, count(*) phrases, max(frags) FROM phrase GROUP BY ALL ORDER BY layer, n").fetchall())
con.execute("CHECKPOINT")
con.close()
print('size', os.path.getsize(DB) // 2**20, 'MB')
