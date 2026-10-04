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


DEFAULT_DADJI_LEXICON = [
    # Kinship & Family Names
    {"word": "Dadaji", "category": "family", "phonetic": "D320"},
    {"word": "Dadi", "category": "family", "phonetic": "D300"},
    {"word": "Ramesh", "category": "family", "phonetic": "R520"},
    {"word": "Sunita", "category": "family", "phonetic": "S530"},
    {"word": "Rohan", "category": "family", "phonetic": "R500"},
    {"word": "Priya", "category": "family", "phonetic": "P600"},
    {"word": "Aarav", "category": "family", "phonetic": "A610"},
    {"word": "Ananya", "category": "family", "phonetic": "A550"},
    {"word": "Chachi", "category": "family", "phonetic": "C200"},
    {"word": "Chacha", "category": "family", "phonetic": "C200"},
    {"word": "Bhabhi", "category": "family", "phonetic": "B100"},
    {"word": "Bhaiya", "category": "family", "phonetic": "B000"},
    {"word": "Tauji", "category": "family", "phonetic": "T200"},
    {"word": "Maasi", "category": "family", "phonetic": "M200"},
    {"word": "Mausi", "category": "family", "phonetic": "M200"},
    {"word": "Nana", "category": "family", "phonetic": "N500"},
    {"word": "Nani", "category": "family", "phonetic": "N500"},
    # Food & Dinner items
    {"word": "Dal makhani", "category": "food", "phonetic": "D452"},
    {"word": "Paneer", "category": "food", "phonetic": "P560"},
    {"word": "Roti", "category": "food", "phonetic": "R300"},
    {"word": "Chai", "category": "food", "phonetic": "C000"},
    {"word": "Kheer", "category": "food", "phonetic": "K600"},
    {"word": "Subzi", "category": "food", "phonetic": "S120"},
    {"word": "Khana", "category": "food", "phonetic": "K500"},
    {"word": "Pulao", "category": "food", "phonetic": "P400"},
    {"word": "Paratha", "category": "food", "phonetic": "P630"},
    {"word": "Dahi", "category": "food", "phonetic": "D000"},
    # Medicines & Medical terms
    {"word": "Metformin", "category": "medicine", "phonetic": "M316"},
    {"word": "Telmisartan", "category": "medicine", "phonetic": "T452"},
    {"word": "Atorvastatin", "category": "medicine", "phonetic": "A361"},
    {"word": "Ecosprin", "category": "medicine", "phonetic": "E216"},
    {"word": "Blood Sugar", "category": "medicine", "phonetic": "B432"},
    {"word": "Blood Pressure", "category": "medicine", "phonetic": "B431"},
    {"word": "Doctor Verma", "category": "medicine", "phonetic": "D236"},
    {"word": "Apollo Clinic", "category": "medicine", "phonetic": "A142"},
    {"word": "Prescription", "category": "medicine", "phonetic": "P626"},
    # Conversational Hinglish phrases
    {"word": "Haanji", "category": "phrase", "phonetic": "H520"},
    {"word": "Nahin", "category": "phrase", "phonetic": "N500"},
    {"word": "Shukriya", "category": "phrase", "phonetic": "S260"},
    {"word": "Theek hai", "category": "phrase", "phonetic": "T200"},
    {"word": "Achha", "category": "phrase", "phonetic": "A200"},
    {"word": "Jaldi", "category": "phrase", "phonetic": "J430"},
    {"word": "Shanti", "category": "phrase", "phonetic": "S530"},
    {"word": "Beta", "category": "phrase", "phonetic": "B300"},
    {"word": "Beti", "category": "phrase", "phonetic": "B300"},
    {"word": "Bachho", "category": "phrase", "phonetic": "B200"},
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
                for item in DEFAULT_DADJI_LEXICON:
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
