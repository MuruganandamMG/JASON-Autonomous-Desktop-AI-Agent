import json
import sqlite3
import time
from pathlib import Path

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,state TEXT,summary TEXT);
        CREATE TABLE IF NOT EXISTS grants(kind TEXT,identity TEXT,PRIMARY KEY(kind,identity));
        CREATE TABLE IF NOT EXISTS usage(model TEXT,stamp REAL,tokens INTEGER,actual TEXT);
        CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,state TEXT,result TEXT);
        """)
        self.db.execute("UPDATE tasks SET state='INTERRUPTED' WHERE state IN ('RUNNING','VERIFYING')")
        self.db.commit()
    def __enter__(self): return self
    def __exit__(self, *args): self.db.close()
    def task(self, tid, state, summary):
        self.db.execute("INSERT OR REPLACE INTO tasks VALUES(?,?,?)", (tid,state,summary[:1000]))
        self.db.commit()
    def tasks(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM tasks")]
    def grant(self, kind, identity):
        self.db.execute("INSERT OR IGNORE INTO grants VALUES(?,?)", (kind,identity))
        self.db.commit()
    def allowed(self, kind, identity):
        return self.db.execute("SELECT 1 FROM grants WHERE kind=? AND identity=?", (kind,identity)).fetchone() is not None
    def revoke(self):
        self.db.execute("DELETE FROM grants")
        self.db.commit()
    def consume(self,kind,identity):
        self.db.execute("DELETE FROM grants WHERE kind=? AND identity=?",(kind,identity))
        self.db.commit()
    def record_usage(self, model, stamp, tokens):
        cur = self.db.execute("INSERT INTO usage VALUES(?,?,?,?)", (model,stamp,tokens,""))
        self.db.commit()
        return cur.lastrowid
    def reconcile(self, row, actual):
        self.db.execute("UPDATE usage SET actual=? WHERE rowid=?", (json.dumps(actual),row))
        self.db.commit()
    def usage(self):
        return [dict(r) for r in self.db.execute("SELECT rowid,* FROM usage")]
    def operation(self, oid, state, result=""):
        self.db.execute("INSERT OR REPLACE INTO operations VALUES(?,?,?)", (oid,state,result))
        self.db.commit()
    def operation_result(self, oid):
        r = self.db.execute("SELECT * FROM operations WHERE id=?", (oid,)).fetchone()
        return dict(r) if r else None

