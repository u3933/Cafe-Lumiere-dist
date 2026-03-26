"""
MemoryManager - 長期記憶 / 来訪履歴 / 会話ログ管理（本編と同一）
"""
import sqlite3
import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_CREATE_VISITS = """
CREATE TABLE IF NOT EXISTS visits (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  visited_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at      DATETIME,
  duration_min  INTEGER DEFAULT 0,
  message_count INTEGER DEFAULT 0
)"""

_CREATE_MEMORIES = """
CREATE TABLE IF NOT EXISTS memories (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  category    TEXT NOT NULL,
  content     TEXT NOT NULL,
  confidence  REAL DEFAULT 1.0,
  source      TEXT,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_active   INTEGER DEFAULT 1
)"""

_CREATE_CONVERSATION_LOG = """
CREATE TABLE IF NOT EXISTS conversation_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  visit_id   INTEGER REFERENCES visits(id),
  speaker    TEXT NOT NULL,
  message    TEXT NOT NULL,
  logged_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)"""


class MemoryManager:

    def __init__(self, config: dict):
        mem_cfg = config.get("memory", {})
        db_path = mem_cfg.get("db_path", "data/memory.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._initial_memories = mem_cfg.get("initial_memories", [])
        self._current_visit_id: int | None = None
        self._visit_start: datetime | None = None
        self._init_db()
        self._seed_initial_memories()
        logger.info(f"🧠 MemoryManager 初期化: {db_path}")

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_CREATE_VISITS)
            conn.execute(_CREATE_MEMORIES)
            conn.execute(_CREATE_CONVERSATION_LOG)
            conn.commit()

    def _seed_initial_memories(self):
        if not self._initial_memories:
            return
        with self._conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            if count > 0:
                return
            for m in self._initial_memories:
                content = m.get("content", "").strip()
                if not content:
                    continue
                conn.execute(
                    "INSERT INTO memories (category, content, confidence, source) VALUES (?,?,1.0,'初期設定')",
                    (m.get("category", "fact"), content),
                )
            conn.commit()
        logger.info(f"🌱 初期記憶を投入: {len(self._initial_memories)}件")

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def start_visit(self) -> int:
        with self._conn() as conn:
            cur = conn.execute("INSERT INTO visits (visited_at) VALUES (CURRENT_TIMESTAMP)")
            conn.commit()
            self._current_visit_id = cur.lastrowid
            self._visit_start = datetime.now()
            logger.info(f"📅 来訪開始 visit_id={self._current_visit_id}")
            return self._current_visit_id

    def end_visit(self, message_count: int):
        if self._current_visit_id is None:
            return
        duration = int((datetime.now() - self._visit_start).total_seconds() / 60) if self._visit_start else 0
        with self._conn() as conn:
            conn.execute(
                "UPDATE visits SET ended_at=CURRENT_TIMESTAMP, duration_min=?, message_count=? WHERE id=?",
                (duration, message_count, self._current_visit_id),
            )
            conn.commit()
        logger.info(f"📅 来訪終了 visit_id={self._current_visit_id} duration={duration}min messages={message_count}")

    def log_message(self, speaker: str, message: str):
        if self._current_visit_id is None:
            return
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversation_log (visit_id, speaker, message) VALUES (?,?,?)",
                (self._current_visit_id, speaker, message),
            )
            conn.commit()

    def save_memories(self, facts: list[dict]):
        if not facts:
            return
        saved = 0
        with self._conn() as conn:
            for f in facts:
                category = f.get("category", "fact")
                content = f.get("content", "").strip()
                source = f.get("source", "")
                if not content:
                    continue
                row = conn.execute("SELECT id, confidence FROM memories WHERE content=?", (content,)).fetchone()
                if row:
                    new_conf = min(row["confidence"] + 0.1, 2.0)
                    conn.execute(
                        "UPDATE memories SET confidence=?, updated_at=CURRENT_TIMESTAMP, is_active=1 WHERE id=?",
                        (new_conf, row["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO memories (category, content, confidence, source) VALUES (?,?,1.0,?)",
                        (category, content, source),
                    )
                saved += 1
            conn.commit()
        if saved:
            logger.info(f"🧠 記憶保存: {saved}件")

    def get_memories_for_prompt(self, max_count: int = 10) -> str:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT category, content FROM memories WHERE is_active=1 ORDER BY confidence DESC LIMIT ?",
                (max_count,),
            ).fetchall()
        if not rows:
            return ""
        return "\n".join(f"- [{r['category']}] {r['content']}" for r in rows)

    def get_all_memories(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, category, content, confidence, source, created_at, updated_at, is_active "
                "FROM memories ORDER BY confidence DESC, updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_memory(self, memory_id: int, content: str, category: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE memories SET content=?, category=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (content, category, memory_id),
            )
            conn.commit()

    def delete_memory(self, memory_id: int):
        with self._conn() as conn:
            conn.execute("UPDATE memories SET is_active=0 WHERE id=?", (memory_id,))
            conn.commit()

    def restore_memory(self, memory_id: int):
        with self._conn() as conn:
            conn.execute("UPDATE memories SET is_active=1 WHERE id=?", (memory_id,))
            conn.commit()

    def add_memory_manual(self, category: str, content: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO memories (category, content, confidence, source) VALUES (?,?,1.0,'手動追加')",
                (category, content.strip()),
            )
            conn.commit()

    def get_visits(self, limit: int = 30) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, visited_at, ended_at, duration_min, message_count FROM visits ORDER BY visited_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation_log(self, visit_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT speaker, message, logged_at FROM conversation_log WHERE visit_id=? ORDER BY logged_at",
                (visit_id,),
            ).fetchall()
        return [dict(r) for r in rows]
