"""SQLite storage (WAL). Replaces the old bot_data.json, with automatic import."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("botam.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    first_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    source_lang TEXT DEFAULT 'auto',
    target_lang TEXT DEFAULT 'fa',
    count INTEGER DEFAULT 0,
    created_at INTEGER,
    last_seen INTEGER
);
CREATE TABLE IF NOT EXISTS history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    original TEXT, translated TEXT,
    src TEXT, dst TEXT, engine TEXT,
    ts INTEGER
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, id DESC);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""
HISTORY_LIMIT = 20


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            if self.path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    # ── users ──
    def touch_user(self, uid: int, first_name: str = "", username: str = "") -> dict:
        now = int(time.time())
        with self._lock:
            self._conn.execute(
                """INSERT INTO users(id, first_name, username, created_at, last_seen) VALUES(?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET first_name=excluded.first_name,
                   username=excluded.username, last_seen=excluded.last_seen""",
                (uid, first_name or "", username or "", now, now),
            )
            self._conn.commit()
            return dict(self._conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())

    def get_user(self, uid: int) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            return dict(row) if row else None

    def set_langs(self, uid: int, source: str | None = None, target: str | None = None):
        with self._lock:
            if source is not None:
                self._conn.execute("UPDATE users SET source_lang=? WHERE id=?", (source, uid))
            if target is not None:
                self._conn.execute("UPDATE users SET target_lang=? WHERE id=?", (target, uid))
            self._conn.commit()

    def delete_user(self, uid: int):
        with self._lock:
            self._conn.execute("DELETE FROM history WHERE user_id=?", (uid,))
            self._conn.execute("DELETE FROM users WHERE id=?", (uid,))
            self._conn.commit()

    # ── history ──
    def add_translation(self, uid: int, original: str, translated: str, src: str, dst: str, engine: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO history(user_id, original, translated, src, dst, engine, ts) VALUES(?,?,?,?,?,?,?)",
                (uid, original, translated, src, dst, engine, int(time.time())),
            )
            hid = cur.lastrowid
            self._conn.execute(
                "DELETE FROM history WHERE user_id=? AND id NOT IN "
                "(SELECT id FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?)",
                (uid, uid, HISTORY_LIMIT),
            )
            self._conn.execute("UPDATE users SET count=count+1 WHERE id=?", (uid,))
            self._conn.execute(
                "INSERT INTO meta(key,value) VALUES('total_translations','1') "
                "ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+1"
            )
            self._conn.commit()
            return hid

    def recent(self, uid: int, n: int = 5) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM history WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, n)).fetchall()
            return [dict(r) for r in rows]

    def get_item(self, uid: int, hid: int) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM history WHERE id=? AND user_id=?", (hid, uid)).fetchone()
            return dict(row) if row else None

    def clear_history(self, uid: int):
        with self._lock:
            self._conn.execute("DELETE FROM history WHERE user_id=?", (uid,))
            self._conn.commit()

    # ── stats ──
    def rank(self, uid: int) -> tuple[int, int]:
        with self._lock:
            me = self._conn.execute("SELECT count FROM users WHERE id=?", (uid,)).fetchone()
            total = self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if not me:
                return total, total
            better = self._conn.execute("SELECT COUNT(*) FROM users WHERE count>?", (me["count"],)).fetchone()[0]
            return better + 1, total

    def stats(self) -> dict:
        day_ago = int(time.time()) - 86400
        with self._lock:
            users = self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active = self._conn.execute("SELECT COUNT(*) FROM users WHERE last_seen>?", (day_ago,)).fetchone()[0]
            meta = self._conn.execute("SELECT value FROM meta WHERE key='total_translations'").fetchone()
            total = int(meta[0]) if meta else self._conn.execute("SELECT COALESCE(SUM(count),0) FROM users").fetchone()[0]
        return {"users": users, "active_24h": active, "translations": total}

    def all_user_ids(self) -> list[int]:
        with self._lock:
            return [r[0] for r in self._conn.execute("SELECT id FROM users")]

    # ── legacy import (bot_data.json from v6) ──
    def import_legacy_json(self, path: Path | str) -> int:
        path = Path(path)
        if not path.exists() or self.stats()["users"] > 0:
            return 0
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            log.warning("legacy import failed: %s", e)
            return 0
        now, imported = int(time.time()), 0
        with self._lock:
            for uid, u in (data.get("users") or {}).items():
                if not str(uid).lstrip("-").isdigit():
                    continue
                self._conn.execute(
                    "INSERT OR IGNORE INTO users(id, source_lang, target_lang, count, created_at, last_seen) VALUES(?,?,?,?,?,?)",
                    (int(uid), u.get("source_lang", "auto"), u.get("target_lang", "fa"), int(u.get("count", 0)), now, now),
                )
                for h in (u.get("history") or [])[-HISTORY_LIMIT:]:
                    self._conn.execute(
                        "INSERT INTO history(user_id, original, translated, src, dst, engine, ts) VALUES(?,?,?,?,?,?,?)",
                        (int(uid), h.get("original", ""), h.get("translated", ""), h.get("src", "auto"), h.get("tgt", "fa"), "legacy", now),
                    )
                imported += 1
            self._conn.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES('total_translations', ?)", (str(int(data.get("translations", 0))),)
            )
            self._conn.commit()
        log.info("imported %d users from legacy json", imported)
        return imported
