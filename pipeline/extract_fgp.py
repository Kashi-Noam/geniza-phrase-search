"""Friedberg transcriptions out of the restored FIST database (SQL Server, see sq.py) -> two parquet files used by corpus.py:
  ngram_fgp_raw.parquet         every transcription (not translations) in dbo.zzTransForRosetta, the export FGP prepared for NLI Rosetta
  ngram_fgp_not_public.parquet  ids of transcriptions that are not in the public website snapshot (SnpShot.UnitTran), left out of the corpus
The snapshot only holds view levels 0 and 310 (public); records marked 2310 'allowed users only' / 3310 'not for publication' are not in it."""
import pandas as pd, sys, warnings
warnings.filterwarnings('ignore')
OUT = '/nas/archive/haifa-data/noam/fgp_report/'
sys.path.insert(0, OUT)
from sq import conn
cn = conn('FIST')
def sql(q): return pd.read_sql(q, cn)

z = sql("""SELECT ID, InventoryId, fileName, ResearcherNameEng, DateCreated, Language, Sigla, IsTranslation, FileTxt
           FROM dbo.zzTransForRosetta""")
t = z[z.IsTranslation.astype(str) != 'True'].copy()
t.to_parquet(OUT + 'ngram_fgp_raw.parquet')
print('transcriptions', len(t), '| fragments', t.InventoryId.nunique(), '| words', int(t.FileTxt.fillna('').str.split().str.len().sum()))

# public or not: file name -> UnitTranscription.SignatureId -> SnpShot.UnitTran (the website snapshot)
ut = sql("SELECT SignatureId, FileName FROM dbo.UnitTranscription")
snap = sql("SELECT DISTINCT SignatureId, ViewLevelCode FROM SnpShot.UnitTran")
m = t[['ID', 'fileName']].merge(ut, left_on='fileName', right_on='FileName', how='left').merge(snap, on='SignatureId', how='left')
public = m.groupby('ID').ViewLevelCode.apply(lambda s: s.isin([0, 310]).any())
pd.DataFrame({'ID': sorted(public[~public].index)}).to_parquet(OUT + 'ngram_fgp_not_public.parquet')
print('public', int(public.sum()), '| not in the public snapshot', int((~public).sum()))
