"""Tiny SQL helper for the user-space SQL Server: python sq.py "<sql>"  (prints rows)"""
import pymssql, sys
def conn(db='master'):
    pw = open('/nas/archive/haifa-data/noam/mssql/sa_password').read().strip()
    return pymssql.connect(server='127.0.0.1', port=14333, user='sa', password=pw, database=db, autocommit=True, timeout=0, login_timeout=30)
if __name__ == '__main__':
    db = sys.argv[2] if len(sys.argv) > 2 else 'master'
    c = conn(db).cursor()
    c.execute(sys.argv[1])
    while True:
        try:
            if c.description:
                print('\t'.join(d[0] for d in c.description))
                for r in c.fetchall(): print('\t'.join('' if v is None else str(v)[:150] for v in r))
        except pymssql.OperationalError: pass
        if not c.nextset(): break
