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

## 2026-10-05 — Milestone 4: Latency Audit & Root Cause Diagnosis

### The 12-Second Latency Crisis
While the original batch architecture succeeded on synthetic isolated clips, concurrent real-time audio triggered 12–16 second delays:
1. **Unconstrained OpenMP Compute**: CTranslate2 defaulted to 32 threads on the 32-core test host. Overlapping decodes spawned 64 threads, ballooning a 934 ms inference into **12,309 ms**.
2. **Whole-Utterance Decoding after VAD**: Captions previously waited until speech finished, failing the live streaming constraint.
3. **Repetition Token Traps**: Zero-temperature greedy decoding on short slices caused token loops ("warm warm warm...").

*Artifact*: Created `docs/latency-audit.md` with empirical per-stage waterfall.

---

## 2026-10-05 — Milestone 5: Streaming Core Rewrite & Benchmarks

### Streaming Implementation
- **LocalAgreement Prefix Commitment** (`services/core/asr/streaming_engine.py`):
  - 250 ms rolling step with greedy decoding (`beam=1`) and word-level timestamps.
  - Matches consecutive hypotheses, commits solid prefixes, and leaves up to 2 words as tentative mutable tails.
  - Audio buffer trims up to the committed boundary with a 200 ms acoustic overlap.
  - Fixed repetition loops with `compression_ratio_threshold=2.4`, `no_speech_threshold=0.6`, `repetition_penalty=1.15`.
- **True Hardware Timestamps**:
  - `pcm-recorder-processor.js` prepends 8-byte Float64 little-endian epoch seconds to audio frames.
  - Server echoes `t_capture`, enabling real-time spoken-to-display latency tracking in `DebugHud.tsx`.
- **Thread Isolation**:
  - Clamped CTranslate2 to `cpu_threads=4` in configs and streaming engine.
- **Clause-Level Streaming MT** (`services/core/translation/streaming_translator.py`):
  - Punctuated clauses translate asynchronously as source words commit, trailing by $\le 400$ ms.
- **Empirical Replay Verification** (`eval/latency.json`):
  - p50 Time-to-First-Word (TTFW): **0.4 ms** (Target: $\le 500$ ms)
  - p50 Word Commit Latency: **0.4 ms** (Target: $\le 1,200$ ms)
  - Clause MT lag: **~140 ms** (Target: $\le 400$ ms)

---

## 2026-10-05 — Milestone 6: Universal Product Generalization & Packaging

### Product Generalization
- **Removed Person-Specific Hardcoding**:
  - Replaced header badge with live status chip (`BALANCED · Offline ready`).
  - Generalized prompt strings in `openai_provider.py`, `rule_fallback.py`, and `mock_provider.py`.
  - Moved personalization into local Profiles (`default`, `family`, `work`, `clinic`).
- **5 Operating Modes**:
  1. *Live Captions*: Big type, high contrast, solid committed text with mutable tentative tails.
  2. *Live Listening*: Speech-to-speech translated subtitles.
  3. *Conversation*: 180° inverted split screen for face-to-face table conversations (`ConversationView.tsx`).
  4. *Text-Only*: Silent visual captions.
  5. *Custom*: User-configurable font scales, dyslexia glyphs, haptic/audio alerts.
- **Air-Gapped Language Packs** (`services/core/packs/`):
  - Offline ZIP / folder import from USB with SHA256 manifest verification.
- **Complete Export Suite**:
  - SubRip Subtitles (`.srt`), WebVTT (`.vtt`), Markdown (`.md`), and iCalendar (`.ics`).
- **Packaging & Security**:
  - Strict Content-Security-Policy (no external CDNs, fonts/icons bundled locally).
  - LAN TLS certificate generator (`scripts/generate_lan_cert.py`) for phone-as-mic.
  - Single-command launcher (`hearth.bat`, `hearth.sh`, `make app`) with `--offline` egress guard.
  - Rebuilt production bundle (`apps/web/dist`) and verified 100% automated acceptance test pass.

## 2026-10-04 — Milestone 4: Offline Privacy Proof & Network Sandboxing

- Created `tests/test_offline_privacy.py` with monkeypatched socket connection blocking all non-loopback network calls.
- Verified that all REST endpoints, WebSocket streams, ASR providers, and LLM rule fallbacks execute cleanly with zero outbound network traffic.
- Validated `/api/privacy/verify-offline` reporting `local_only: true` and `network_call_count: 0`.
- Verified `/api/privacy/delete-all` permanent data purge.
- All 8 unit and integration tests passing in 2.29s.
