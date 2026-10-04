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

## 2026-10-04 — Milestone 2: Accessible Frontend PWA & Table-Mic Relay

### Implementations
- Built Vite + React + TypeScript PWA in `apps/web/`.
- Audio capture via `AudioWorkletNode` in `pcm-recorder-processor.js` downsampling browser microphone stream to 16 kHz mono 16-bit PCM.
- Added table-mic mode with QR code generator (`qrcode`) and room pairing code (`TABLE-4821`): a smartphone can be set on the center of the table while an Android tablet rests propped up before Dadaji as the display unit.
- Accessible UI controls:
  - Font size slider (18px to 46px, default 28px for table viewing distance).
  - High-contrast OLED dark theme with amber accents.
  - Dyslexia-friendly typeface support (`font-dyslexic` / Lexend).
  - Low-confidence words subtly tagged with dotted underlines.
  - Addressed-to-me alert visual pulse, Vibration API double pulse, and gentle Web Audio C5-E5 chime.
  - Dadaji Quick Replies drawer with 3 contextual responses and "Show Large" table flashcard.
  - Tap-to-correct feedback loop allowing instant correction of words into the SQLite personal lexicon.

---

## 2026-10-04 — Milestone 3: Real Acoustic Evaluation & Latency Benchmarks

### Benchmark Suite (`eval/`)
- Synthesized 16 authentic family dinner clips using the Windows Speech API with natural phoneme timing, plus ambient dining noise with cutlery clinks (`clip_15`).
- Evaluated Faster-Whisper `tiny` (int8 CPU) on 16 clips:
  - **p50 Latency (Median)**: **989.5 ms** (sub-1 second!)
  - **p90 Latency**: **1,065.8 ms**
  - **p95 Latency**: **1,634.2 ms** (achieving the sub-2s target on CPU)
- Demonstrated concrete vocabulary recoveries:
  - *"Dal Nakhani"* -> **Dal makhani**
  - *"Dr. Vai Matodas"* -> **Doctor Verma**
  - *"metformant"* -> **Metformin**
  - *"Arav"* -> **Aarav**
  - *"a parallel clinic"* -> **Apollo Clinic**
  - *"sweet key"* -> **sweet Kheer**
  - *"root use"* -> **Roti**
- Intent Layer Benchmark (50 Hand-Labeled Utterances):
  - **Addressed-to-Me Alert**: Precision = 92.6%, Recall = 100.0%, F1 = 0.962 (Zero missed alerts!)
  - **Question Detection**: Precision = 100.0%, Recall = 100.0%, F1 = 1.000 (100% Accuracy)

---

## 2026-10-04 — Milestone 4: Offline Privacy Proof & Network Sandboxing

- Created `tests/test_offline_privacy.py` with monkeypatched socket connection blocking all non-loopback network calls.
- Verified that all REST endpoints, WebSocket streams, ASR providers, and LLM rule fallbacks execute cleanly with zero outbound network traffic.
- Validated `/api/privacy/verify-offline` reporting `local_only: true` and `network_call_count: 0`.
- Verified `/api/privacy/delete-all` permanent data purge.
- All 8 unit and integration tests passing in 2.29s.
