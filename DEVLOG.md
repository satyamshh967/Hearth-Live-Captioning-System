# Hearth — Development Log (DEVLOG.md)

This log records architecture decisions, milestones, benchmark results, and field findings for **Hearth**, built for the dev.to Hacktoberfest Weekend Challenge: *Build for a Friend*.

---

## 2026-10-04 — Project Kickoff & Persona Definition

### The Friend
- **Name / Alias**: Ramesh ("Dadaji")
- **Age & Situation**: 76 years old, progressive bilateral sensorineural age-related hearing loss. Struggles at lively family dinners where 4–6 people speak simultaneously, laugh, and code-switch rapidly between Hindi and English mid-sentence. Tends to quietly withdraw from dinner conversations because he cannot follow fast-moving banter.
- **Language Profile**: Hinglish (Hindi + English colloquial code-switching, e.g., *"Dadaji, aapne Metformin li kya with warm water?"* or *"Priya is coming from Gurgaon for dinner, hum dal makhani banayein?"*).
- **Physical Environment**: Family dining table, 3 to 6 feet distance from speakers, background ambient noise (cutlery, ceiling fan, distant pressure cooker).
- **Devices**:
  - Tablet: 10-inch Android tablet (display unit prop up on table stand).
  - Phone: Budget Android smartphone (table-mic mode placed in the center of the table).
  - Backup: Windows / Linux laptop.
- **Key Vocabulary (40+ terms)**:
  - *Names & Kinship*: Dadaji, Dadi, Ramesh, Sunita, Rohan, Priya, Aarav, Ananya, Chachi, Chacha, Bhabhi, Bhaiya, Maasi, Nana, Nani, Mausi, Tauji
  - *Dishes & Food*: Dal makhani, Paneer, Roti, Chai, Kheer, Subzi, Khana, Pulao, Paratha
  - *Medicines & Health*: Metformin, Telmisartan, Atorvastatin, Ecosprin, BP, Blood Sugar, Clinic, Apollo, Doctor Verma, Prescription
  - *Conversational Hindi*: Haanji, Nahin, Shukriya, Achha, Theek hai, Jaldi, Thoda, Bahut, Shanti, Kripya, Beta, Beti, Bachho
- **Frustrations with Existing Captioning Tools**:
  - Cloud latency (4–5s delay ruins the punchline of family jokes).
  - Lack of speaker differentiation (a continuous wall of grey text).
  - Poor handling of Hinglish (Hindi terms get mutilated into nonsensical English phonetics).
  - Privacy concerns (doesn't want personal health/family talk streamed to tech company servers).
  - Small, unreadable fonts from a seated distance across the dinner table.
  - Zero alerting when someone directly addresses him by name.

---

## Architecture Decisions

1. **Strictly Decoupled Real-Time Path**:
   - Audio -> Silero VAD -> faster-whisper ASR -> WebSocket -> UI.
   - LLMs are **never** on the real-time caption latency path. The caption stream must maintain sub-2s final latency on CPU.
2. **Offline-First / Zero-Telemetry Core**:
   - All models run locally on device (faster-whisper, local embeddings for diarization, local/Ollama LLM with deterministic rule-based fallbacks).
   - Strict privacy boundary: no external cloud endpoints, audio discarded after streaming frames, transcripts stored strictly in local SQLite with configurable auto-deletion.
3. **Hardware Profiles (`tiny`, `balanced`, `quality`)**:
   - `tiny`: Whisper tiny (int8, CPU/Pi-friendly, <500ms chunk latency).
   - `balanced`: Whisper base (int8, ideal for laptop CPU, high accuracy on code-switching).
   - `quality`: Whisper small / large-v3-turbo (GPU or high-end multi-core CPU).
4. **Vocabulary Biasing & Correction Pipeline**:
   - Hotword biasing in Whisper (`initial_prompt` / `hotwords`).
   - Post-ASR phonetic & token fuzzy alignment using `rapidfuzz` + Soundex/Metaphone matching.
   - "Correct-to-learn" user feedback loop directly injecting into local SQLite lexicon.
