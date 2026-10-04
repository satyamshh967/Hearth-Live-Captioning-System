import re
from typing import List, Tuple, Optional
from rapidfuzz import fuzz, process
from ..store.lexicon import LexiconStore, soundex
from .provider import ASRResult, WordConfidence


class LexiconPostProcessor:
    def __init__(self, lexicon_store: LexiconStore, fuzzy_threshold: float = 78.0):
        self.lexicon_store = lexicon_store
        self.fuzzy_threshold = fuzzy_threshold

    def clean_text(self, text: str) -> str:
        """Strip redundant spaces and normalize common Hinglish transcription artifacts."""
        text = re.sub(r'\s+', ' ', text).strip()
        # In Hinglish ASR, the honorific 'ji' is often misrecognized as single letter 'g' (e.g., 'dada g' -> 'dada ji')
        text = re.sub(r'\b([a-zA-Z]{3,})\s+[gG]\b', r'\1 ji', text)
        return text

    def correct_text(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Fuzzy & phonetic post-correction against the personal lexicon.
        Returns (corrected_text, list_of_corrections [(original, corrected)]).
        """
        text = self.clean_text(text)
        words = text.split()
        if not words:
            return text, []

        lexicon_items = self.lexicon_store.get_all()
        lex_map = {item["word"].lower(): item["word"] for item in lexicon_items}
        phonetic_map = {item["phonetic"]: item["word"] for item in lexicon_items if item.get("phonetic")}
        lex_keys = list(lex_map.keys())

        corrected_tokens = []
        corrections_made = []

        i = 0
        n = len(words)
        while i < n:
            matched = False

            # Check 2-word n-gram (e.g., "dal makhani", "blood pressure", or split words like "matt forman" -> "Metformin", "dada ji" -> "Dadaji")
            if i + 1 < n:
                bigram = f"{words[i]} {words[i+1]}".strip(".,!?\"'")
                squashed_bigram = f"{words[i]}{words[i+1]}".strip(".,!?\"'").lower()
                clean_bigram = bigram.lower()
                
                # Direct check
                if clean_bigram in lex_map:
                    target = lex_map[clean_bigram]
                    punct = words[i+1][-1] if words[i+1][-1] in ".,!?" else ""
                    corrected_tokens.append(f"{target}{punct}")
                    if bigram != target:
                        corrections_made.append((bigram, target))
                    i += 2
                    continue
                
                # Check squashed bigram against single words in lexicon (e.g., "matt forman" -> "Metformin", "dada ji" -> "Dadaji")
                best_squashed = process.extractOne(squashed_bigram, lex_keys, scorer=fuzz.ratio)
                if best_squashed and best_squashed[1] >= 72.0:
                    target = lex_map[best_squashed[0]]
                    punct = words[i+1][-1] if words[i+1][-1] in ".,!?" else ""
                    corrected_tokens.append(f"{target}{punct}")
                    corrections_made.append((bigram, target))
                    i += 2
                    continue

                # Fuzzy check on bigram
                best_bigram = process.extractOne(clean_bigram, lex_keys, scorer=fuzz.ratio)
                if best_bigram and best_bigram[1] >= 75.0:
                    target = lex_map[best_bigram[0]]
                    punct = words[i+1][-1] if words[i+1][-1] in ".,!?" else ""
                    corrected_tokens.append(f"{target}{punct}")
                    corrections_made.append((bigram, target))
                    i += 2
                    continue

            # Single word check
            token = words[i]
            clean_token = token.strip(".,!?\"'")
            punct = token[len(clean_token):] if len(token) > len(clean_token) else ""
            clean_lower = clean_token.lower()

            if not clean_token:
                corrected_tokens.append(token)
                i += 1
                continue

            # Exact match case normalization
            if clean_lower in lex_map:
                target = lex_map[clean_lower]
                corrected_tokens.append(f"{target}{punct}")
                i += 1
                continue

            # Phonetic match check
            token_soundex = soundex(clean_token)
            if token_soundex in phonetic_map and len(clean_token) >= 4:
                target = phonetic_map[token_soundex]
                # Validate with fuzzy ratio to avoid false positives
                ratio = fuzz.ratio(clean_lower, target.lower())
                if ratio >= 65.0:
                    corrected_tokens.append(f"{target}{punct}")
                    corrections_made.append((clean_token, target))
                    i += 1
                    continue

            # Fuzzy match check
            best_match = process.extractOne(clean_lower, lex_keys, scorer=fuzz.ratio)
            if best_match and best_match[1] >= self.fuzzy_threshold:
                target = lex_map[best_match[0]]
                # Don't replace tiny common words like "the", "in", "to" with names
                if len(clean_token) >= 3 or best_match[1] >= 90.0:
                    corrected_tokens.append(f"{target}{punct}")
                    corrections_made.append((clean_token, target))
                    i += 1
                    continue

            # Keep original word
            corrected_tokens.append(token)
            i += 1

        final_text = " ".join(corrected_tokens)
        return final_text, corrections_made

    def process_result(self, result: ASRResult) -> ASRResult:
        """Apply post-correction to full ASRResult including word-level tokens."""
        corrected_text, corrections = self.correct_text(result.text)
        result.text = corrected_text

        # Re-align word tokens if corrections occurred
        if corrections:
            new_words = []
            for w in result.words:
                clean_w = w.word.strip(".,!?\"'")
                matched = False
                for orig, corr in corrections:
                    if clean_w.lower() == orig.lower():
                        w.word = corr
                        matched = True
                        break
                new_words.append(w)
            result.words = new_words

        return result
