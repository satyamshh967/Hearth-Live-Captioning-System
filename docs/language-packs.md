# Hearth — Language Pack Plugin Specification

Hearth is engineered to support regional dialects, multilingual code-switching, and specialized vocabulary sets across the globe through swappable language packs.

---

## 1. Directory Structure

A language pack is a standalone folder placed under `configs/language_packs/<pack_id>/`:

```
configs/language_packs/hi_in/
  manifest.json
  lexicon.json
  prompts/
    addressed_check.yaml
    quick_replies.yaml
  phonetics.json
```

---

## 2. Manifest Schema (`manifest.json`)

```json
{
  "id": "hi_in",
  "name": "Hindi-English Colloquial (Hinglish)",
  "version": "1.0.0",
  "author": "Hearth Open-Source Community",
  "license": "Apache-2.0",
  "asr": {
    "recommended_model": "base",
    "language_code": "hi",
    "allow_multilingual_autodetect": true
  },
  "tts_voice": "hi-IN",
  "honorifics": ["ji", "sahab", "babu", "dada", "nana", "chachi", "tauji"]
}
```

---

## 3. Seed Lexicon (`lexicon.json`)

Defines regional dishes, medicines, kinship titles, and cultural terms with pre-computed phonetic codes:

```json
[
  {
    "word": "Dal makhani",
    "category": "food",
    "phonetic": "D452",
    "aliases": ["daal makhni", "dal makhny", "dal nakhani"]
  },
  {
    "word": "Metformin",
    "category": "medicine",
    "phonetic": "M316",
    "aliases": ["metformant", "matt forman"]
  }
]
```

---

## 4. Contributing a New Language Pack

Adding a new language pack takes less than 30 minutes:
1. Copy the template from `configs/language_packs/template/`.
2. Add your culture's top 30–50 kinship terms, common household dishes, and local phrases to `lexicon.json`.
3. Provide culturally appropriate affirmative, polite declining, and deferring quick replies in `quick_replies.yaml`.
4. Open a Pull Request!
