import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import datetime
import uuid


class SessionStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "hearth.db")
        else:
            self.db_path = db_path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS utterances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    utt_id TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL,
                    plain_text TEXT,
                    lang TEXT,
                    start_sec REAL,
                    end_sec REAL,
                    confidence REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    time_or_date TEXT,
                    confirmed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS speaker_names (
                    speaker_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    color TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    def create_session(self, title: str = "Family Dinner") -> str:
        session_id = str(uuid.uuid4())[:8]
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, title)
                VALUES (?, ?)
            """, (session_id, title))
            conn.commit()
        return session_id

    def list_sessions(self) -> List[Dict]:
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT s.session_id, s.title, s.summary, s.created_at, s.closed_at,
                       COUNT(u.id) as utterance_count
                FROM sessions s
                LEFT JOIN utterances u ON s.session_id = u.session_id
                GROUP BY s.session_id
                ORDER BY s.created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_session(self, session_id: str) -> Optional[Dict]:
        with self._get_conn() as conn:
            s_cur = conn.execute("SELECT session_id, title, summary, created_at, closed_at FROM sessions WHERE session_id = ?", (session_id,))
            session = s_cur.fetchone()
            if not session:
                return None
            res = dict(session)
            
            u_cur = conn.execute("""
                SELECT utt_id, speaker, text, plain_text, lang, start_sec, end_sec, confidence, timestamp
                FROM utterances WHERE session_id = ? ORDER BY id ASC
            """, (session_id,))
            res["utterances"] = [dict(r) for r in u_cur.fetchall()]

            m_cur = conn.execute("""
                SELECT id, category, title, detail, time_or_date, confirmed
                FROM memories WHERE session_id = ? ORDER BY id ASC
            """, (session_id,))
            res["memories"] = [dict(r) for r in m_cur.fetchall()]
            return res

    def append_utterance(self, session_id: str, utt_id: str, speaker: str, text: str,
                         lang: str = "en", start_sec: float = 0.0, end_sec: float = 0.0,
                         confidence: float = 1.0, plain_text: Optional[str] = None):
        with self._get_conn() as conn:
            # Ensure session exists
            conn.execute("INSERT OR IGNORE INTO sessions (session_id, title) VALUES (?, 'Live Session')", (session_id,))
            conn.execute("""
                INSERT INTO utterances (session_id, utt_id, speaker, text, plain_text, lang, start_sec, end_sec, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, utt_id, speaker, text, plain_text, lang, start_sec, end_sec, confidence))
            conn.commit()

    def update_session_summary(self, session_id: str, summary: str):
        with self._get_conn() as conn:
            conn.execute("UPDATE sessions SET summary = ? WHERE session_id = ?", (summary, session_id))
            conn.commit()

    def add_memory(self, session_id: str, category: str, title: str, detail: str, time_or_date: Optional[str] = None) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO memories (session_id, category, title, detail, time_or_date)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, category, title, detail, time_or_date))
            conn.commit()
            return cursor.lastrowid

    def toggle_memory_confirmation(self, memory_id: int) -> bool:
        with self._get_conn() as conn:
            conn.execute("UPDATE memories SET confirmed = 1 - confirmed WHERE id = ?", (memory_id,))
            conn.commit()
            cursor = conn.execute("SELECT confirmed FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            return bool(row["confirmed"]) if row else False

    def rename_speaker(self, speaker_id: str, display_name: str, color: Optional[str] = None):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO speaker_names (speaker_id, display_name, color, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(speaker_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    color = COALESCE(excluded.color, speaker_names.color),
                    updated_at = CURRENT_TIMESTAMP;
            """, (speaker_id, display_name, color))
            # Also update past utterances with this speaker_id
            conn.execute("UPDATE utterances SET speaker = ? WHERE speaker = ?", (display_name, speaker_id))
            conn.commit()

    def get_speaker_names(self) -> Dict[str, str]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT speaker_id, display_name FROM speaker_names")
            return {row["speaker_id"]: row["display_name"] for row in cursor.fetchall()}

    def auto_cleanup(self, retention_days: int = 7):
        """Purge transcripts older than retention_days."""
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff_str,))
            conn.commit()

    def delete_everything(self):
        """Privacy proof: completely clear all sessions, utterances, and memories."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM memories")
            conn.execute("DELETE FROM utterances")
            conn.execute("DELETE FROM sessions")
            conn.commit()

    def export_markdown(self, session_id: str) -> str:
        session = self.get_session(session_id)
        if not session:
            return "# Session Not Found\n"
        
        md = [f"# Hearth Transcript: {session['title']}", f"*Recorded on: {session['created_at']}*\n"]
        if session.get("summary"):
            md.append("## Summary\n" + session["summary"] + "\n")
            
        if session.get("memories"):
            md.append("## Things to Remember")
            for m in session["memories"]:
                status = "[x]" if m["confirmed"] else "[ ]"
                time_str = f" ({m['time_or_date']})" if m.get("time_or_date") else ""
                md.append(f"- {status} **{m['title']}**{time_str}: {m['detail']}")
            md.append("")
            
        md.append("## Transcript")
        for u in session.get("utterances", []):
            time_tag = f"[{u['start_sec']:.1f}s - {u['end_sec']:.1f}s]"
            md.append(f"**{u['speaker']}** {time_tag}: {u['text']}")
            if u.get("plain_text"):
                md.append(f"> *Simplified*: {u['plain_text']}")
                
        return "\n".join(md)

    def export_ics(self, session_id: str) -> str:
        """Export session memory items as an iCalendar (.ics) format for calendar apps."""
        session = self.get_session(session_id)
        if not session:
            return ""
            
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Hearth Assistive Captions//EN"
        ]
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        
        for m in session.get("memories", []):
            uid = f"hearth-mem-{m['id']}@localhost"
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now_str}",
                f"SUMMARY:Hearth Note: {m['title']}",
                f"DESCRIPTION:{m['detail']}",
                "END:VEVENT"
            ])
            
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)
