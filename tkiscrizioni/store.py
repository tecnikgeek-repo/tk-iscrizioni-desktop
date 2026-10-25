"""Archivio locale (SQLite) delle intestazioni analizzate e delle note dell'utente sui servizi.
Contiene mittenti, oggetti e date delle email lette: resta su questo computer (cartella dei dati)."""
import os
import sqlite3
import threading
import time

from tkiscrizioni import classify
from tkiscrizioni.util import data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, provider TEXT, host TEXT, port INTEGER DEFAULT 993,
  auth TEXT DEFAULT 'password', last_scan REAL DEFAULT 0, last_error TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS folders (
  account_id INTEGER, name TEXT, uidvalidity INTEGER, last_uid INTEGER DEFAULT 0, PRIMARY KEY (account_id, name));
CREATE TABLE IF NOT EXISTS messages (
  account_id INTEGER, folder TEXT, uid INTEGER, ts REAL, from_addr TEXT, from_name TEXT, domain TEXT,
  subject TEXT, unsub TEXT, unsub_post INTEGER, flags INTEGER, PRIMARY KEY (account_id, folder, uid));
CREATE INDEX IF NOT EXISTS messages_domain ON messages(domain);
CREATE TABLE IF NOT EXISTS services (domain TEXT PRIMARY KEY, status TEXT DEFAULT '', note TEXT DEFAULT '');
"""
# 2 (versione 1.1.0): i link di disiscrizione valgono solo con DKIM verificato. Quelli salvati prima non
# erano controllati: si tolgono e la prossima analisi rilegge le intestazioni (anche l'esito DKIM).
VERSIONE_ARCHIVIO = 2


class Store:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "archivio.db")
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self._migra()

    def _migra(self):
        with self.lock:
            ver = self.db.execute("PRAGMA user_version").fetchone()[0]
            if ver < 2:
                self.db.execute("UPDATE messages SET unsub='', unsub_post=0")
                self.db.execute("UPDATE folders SET last_uid=0")
            if ver < VERSIONE_ARCHIVIO:
                self.db.execute(f"PRAGMA user_version={int(VERSIONE_ARCHIVIO)}")
            self.db.commit()

    @staticmethod
    def _limite():
        """Oltre questa data un'email è «dal futuro» (data falsa): non conta per l'ultima email né per il link."""
        return time.time() + classify.FUTURO_TOLLERATO

    def q(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    def x(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur

    # ---- caselle
    def accounts(self):
        return [dict(r) for r in self.q("SELECT a.*, (SELECT COUNT(*) FROM messages m WHERE m.account_id=a.id) n "
                                        "FROM accounts a ORDER BY a.id")]

    def add_account(self, email, provider, host, port, auth):
        self.x("INSERT INTO accounts(email,provider,host,port,auth) VALUES(?,?,?,?,?) "
               "ON CONFLICT(email) DO UPDATE SET provider=excluded.provider, host=excluded.host, port=excluded.port, "
               "auth=excluded.auth", (email, provider, host, port, auth))
        return self.q("SELECT id FROM accounts WHERE email=?", (email,))[0]["id"]

    def remove_account(self, account_id):
        with self.lock:
            for t in ("messages", "folders"):
                self.db.execute(f"DELETE FROM {t} WHERE account_id=?", (account_id,))
            self.db.execute("DELETE FROM accounts WHERE id=?", (account_id,))
            self.db.commit()
        self.vacuum_later = True

    def set_scan(self, account_id, ts, error=""):
        self.x("UPDATE accounts SET last_scan=?, last_error=? WHERE id=?", (ts, error, account_id))

    # ---- cartelle e messaggi
    def folder_state(self, account_id, name):
        r = self.q("SELECT uidvalidity, last_uid FROM folders WHERE account_id=? AND name=?", (account_id, name))
        return (r[0]["uidvalidity"], r[0]["last_uid"]) if r else (None, 0)

    def reset_folder(self, account_id, name, uidvalidity):
        with self.lock:
            self.db.execute("DELETE FROM messages WHERE account_id=? AND folder=?", (account_id, name))
            self.db.execute("INSERT OR REPLACE INTO folders(account_id,name,uidvalidity,last_uid) VALUES(?,?,?,0)",
                            (account_id, name, uidvalidity))
            self.db.commit()

    def save_batch(self, account_id, folder, rows, last_uid):
        with self.lock:
            self.db.executemany(
                "INSERT OR REPLACE INTO messages(account_id,folder,uid,ts,from_addr,from_name,domain,subject,unsub,"
                "unsub_post,flags) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                [(account_id, folder, uid, r["ts"], r["from_addr"], r["from_name"], r["domain"], r["subject"],
                  r["unsub"], r["unsub_post"], r["flags"]) for uid, r in rows])
            self.db.execute("UPDATE folders SET last_uid=MAX(last_uid,?) WHERE account_id=? AND name=?",
                            (last_uid, account_id, folder))
            self.db.commit()

    # ---- servizi
    def services(self):
        """Un dizionario per dominio con conteggi, date, categoria, nome, link di disiscrizione e note."""
        own = {a["email"].rpartition("@")[2] for a in self.accounts()}
        own -= classify.FREEMAIL
        limite = self._limite()
        rows = self.q(
            "SELECT domain, COUNT(*) n, MIN(CASE WHEN ts>0 AND ts<=? THEN ts END) first, "
            "MAX(CASE WHEN ts<=? THEN ts ELSE 0 END) last, "
            "SUM((flags&1)>0) acc, SUM((flags&2)>0) sec, SUM((flags&4)>0) pur, SUM((flags&8)>0) lst, "
            "GROUP_CONCAT(DISTINCT account_id) accs FROM messages WHERE domain<>'' GROUP BY domain", (limite, limite))
        names = {}
        for r in self.q("SELECT domain, from_name, COUNT(*) c FROM messages WHERE from_name<>'' "
                        "GROUP BY domain, from_name ORDER BY c DESC"):
            names.setdefault(r["domain"], []).append((r["from_name"], r["c"]))
        # il link dell'email più recente (con DKIM verificato: gli altri non vengono salvati), mai da date future
        unsub = {r["domain"]: (r["unsub"], r["unsub_post"]) for r in self.q(
            "SELECT domain, unsub, unsub_post, MAX(ts) FROM messages WHERE unsub<>'' AND ts<=? GROUP BY domain",
            (limite,))}
        notes = {r["domain"]: (r["status"], r["note"]) for r in self.q("SELECT * FROM services")}
        out = []
        for r in rows:
            d = r["domain"]
            out.append({
                "domain": d, "name": classify.nice_name(names.get(d, []), d), "n": r["n"],
                "first": r["first"] or 0, "last": r["last"] or 0, "acc": r["acc"], "sec": r["sec"],
                "pur": r["pur"], "lst": r["lst"], "accounts": [int(x) for x in str(r["accs"] or "").split(",") if x],
                "cat": classify.category(d, r["acc"], r["sec"], r["pur"], r["lst"], own),
                "unsub": unsub.get(d, ("", 0))[0], "unsub_post": unsub.get(d, ("", 0))[1],
                "status": notes.get(d, ("", ""))[0], "note": notes.get(d, ("", ""))[1],
            })
        return out

    def recent(self, domain, limit=12):
        return [dict(r) for r in self.q(
            "SELECT m.ts, m.subject, m.from_addr, m.flags, a.email account FROM messages m "
            "LEFT JOIN accounts a ON a.id=m.account_id WHERE m.domain=? "
            "ORDER BY CASE WHEN m.ts<=? THEN m.ts ELSE 0 END DESC LIMIT ?", (domain, self._limite(), limit))]

    def set_status(self, domain, status=None, note=None):
        cur = self.q("SELECT status, note FROM services WHERE domain=?", (domain,))
        s, n = (cur[0]["status"], cur[0]["note"]) if cur else ("", "")
        self.x("INSERT OR REPLACE INTO services(domain,status,note) VALUES(?,?,?)",
               (domain, s if status is None else status, n if note is None else note))

    def total_messages(self):
        return self.q("SELECT COUNT(*) c FROM messages")[0]["c"]
