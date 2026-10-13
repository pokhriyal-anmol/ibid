import sqlite3, sys
db = sqlite3.connect("file:data/index/ibid.sqlite?mode=ro", uri=True)
for c in sys.argv[1:]:
    r = db.execute("SELECT text FROM provision WHERE citation = ?", (c,)).fetchone()
    print(c, "::", " ".join(r[0].split()) if r else "NOT IN INDEX")
