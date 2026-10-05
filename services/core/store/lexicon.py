import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from rapidfuzz import process, fuzz


def soundex(name: str) -> str:
    """Compute basic English/Indic Soundex code for phonetic matching."""
    name = name.upper().strip()
    if not name:
        return ""
    
    first_letter = name[0]
    tail = name[1:]
    
    char_map = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    
    encoded = []
    prev_code = char_map.get(first_letter, '0')
    for char in tail:
        code = char_map.get(char, '0')
        if code != '0' and code != prev_code:
            encoded.append(code)
        prev_code = code
        if len(encoded) >= 3:
            break
            
    padded = (first_letter + "".join(encoded) + "000")[:4]
    return padded


DEFAULT_LEXICON = [
    # Everyday conversational and polite words
    {"word": "Hello", "category": "phrase", "phonetic": "H400"},
    {"word": "Thank you", "category": "phrase", "phonetic": "T520"},
    {"word": "Please", "category": "phrase", "phonetic": "P420"},
    {"word": "Welcome", "category": "phrase", "phonetic": "W425"},
    {"word": "Excuse me", "category": "phrase", "phonetic": "E225"},
    {"word": "Yes", "category": "phrase", "phonetic": "Y200"},
    {"word": "No", "category": "phrase", "phonetic": "N000"},
    {"word": "Tomorrow", "category": "general", "phonetic": "T560"},
    {"word": "Today", "category": "general", "phonetic": "T300"},
    {"word": "Meeting", "category": "general", "phonetic": "M352"},
    {"word": "Family", "category": "general", "phonetic": "F540"},
    {"word": "Water", "category": "general", "phonetic": "W360"},
    {"word": "Coffee", "category": "general", "phonetic": "C100"},
    {"word": "Tea", "category": "general", "phonetic": "T000"},
    {"word": "Breakfast", "category": "food", "phonetic": "B621"},
    {"word": "Dinner", "category": "food", "phonetic": "D560"},
    {"word": "Medicine", "category": "medicine", "phonetic": "M325"},
    {"word": "Doctor", "category": "medicine", "phonetic": "D236"},
    {"word": "Appointment", "category": "medicine", "phonetic": "A153"},
    {"word": "Prescription", "category": "medicine", "phonetic": "P626"},
]


class LexiconStore:
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
                CREATE TABLE IF NOT EXISTS lexicon (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE NOT NULL,
                    phonetic TEXT NOT NULL,
                    category TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    user_confirmed INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original TEXT NOT NULL,
                    corrected TEXT NOT NULL,
                    context TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

            # Seed default lexicon if empty
            cursor = conn.execute("SELECT COUNT(*) as count FROM lexicon")
            if cursor.fetchone()["count"] == 0:
                for item in DEFAULT_LEXICON:
                    phonetic = item.get("phonetic") or soundex(item["word"])
                    conn.execute("""
                        INSERT OR IGNORE INTO lexicon (word, phonetic, category, user_confirmed)
                        VALUES (?, ?, ?, 1)
                    """, (item["word"], phonetic, item["category"]))
                conn.commit()

    def get_all(self) -> List[Dict]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT id, word, phonetic, category, frequency, user_confirmed FROM lexicon ORDER BY category, word")
            return [dict(row) for row in cursor.fetchall()]

    def add_or_update(self, word: str, category: str = "custom", user_confirmed: bool = True) -> Dict:
        word = word.strip()
        phonetic = soundex(word)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO lexicon (word, phonetic, category, frequency, user_confirmed)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(word) DO UPDATE SET
                    frequency = frequency + 1,
                    user_confirmed = MAX(user_confirmed, excluded.user_confirmed);
            """, (word, phonetic, category, 1 if user_confirmed else 0))
            conn.commit()
            cursor = conn.execute("SELECT id, word, phonetic, category, frequency, user_confirmed FROM lexicon WHERE word = ?", (word,))
            return dict(cursor.fetchone())

    def delete_word(self, word: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM lexicon WHERE LOWER(word) = LOWER(?)", (word.strip(),))
            conn.commit()
            return cursor.rowcount > 0

    def record_correction(self, original: str, corrected: str, context: Optional[str] = None):
        """Record a word correction pair and add the corrected word to the lexicon."""
        original = original.strip()
        corrected = corrected.strip()
        if not corrected:
            return
            
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO corrections (original, corrected, context)
                VALUES (?, ?, ?)
            """, (original, corrected, context))
            conn.commit()
            
        self.add_or_update(corrected, category="correction", user_confirmed=True)

    def get_corrections(self) -> List[Dict]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT id, original, corrected, context, timestamp FROM corrections ORDER BY timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_prompt_biasing_string(self) -> str:
        """Returns comma-separated top words for Whisper initial_prompt biasing."""
        items = self.get_all()
        words = [item["word"] for item in items]
        return ", ".join(words[:45])

    def find_best_match(self, candidate: str, threshold: float = 80.0) -> Optional[Tuple[str, float]]:
        """Fuzzy match candidate against all words in lexicon."""
        all_words = [item["word"] for item in self.get_all()]
        if not all_words:
            return None
            
        result = process.extractOne(candidate, all_words, scorer=fuzz.ratio)
        if result and result[1] >= threshold:
            return result[0], result[1]
        return None

    def load_profile_vocabulary(self, words: List[str], category: str = "profile"):
        """Imports terms from an active Profile into the personal lexicon."""
        with self._get_conn() as conn:
            for w in words:
                phonetic = soundex(w)
                conn.execute("""
                    INSERT OR IGNORE INTO lexicon (word, phonetic, category, user_confirmed)
                    VALUES (?, ?, ?, 1)
                """, (w, phonetic, category))
            conn.commit()
