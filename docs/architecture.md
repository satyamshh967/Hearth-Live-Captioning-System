# Hearth — Architecture & Technical Design

Hearth is a fully offline, private, live captioning and instant speech translation system. It is designed for multi-speaker conversations, noisy group environments, and cross-language dialogues without internet connectivity, cloud telemetry, or third-party APIs.

---

## 1. Core Architecture Diagram

```mermaid
flowchart TD
    subgraph Client ["Client Layer (Apps/Web PWA)"]
        Worklet["AudioWorklet (pcm-recorder-processor.js)\n16kHz Mono PCM16 + Float64 t_capture header"]
        Display["Live Caption Stream\nSolid Committed Words + 55% Opacity Tentative Tail"]
        ConvSplit["180° Inverted Conversation View\nFace-to-Face Split Screen"]
        Hud["Live Latency Waterfall HUD (Ctrl+Shift+L)"]
    end

    subgraph StreamingCore ["Streaming Critical Path (Live <= 500ms TTFW)"]
        WS["FastAPI Streaming WebSocket Server\n(/ws?room=TABLE-101&role=all)"]
        ASRWorker["Streaming ASR Engine\n(CTranslate2 int8, cpu_threads=4, beam=1)"]
        LocalAgree["LocalAgreement Streaming Policy\nWord Timestamps + Audio Window Trimming"]
        MTWorker["Clause-Based Streaming Translator\n(Terminology Protection + Offline Lexicon)"]
        DiarWorker["Lightweight Centroid Diarizer\n(128-dim Acoustic Embeddings)"]
    end

    subgraph AsyncIntelligence ["Asynchronous Intelligence (Non-Blocking)"]
        RuleLLM["Deterministic Rule-Based Fallback\n(< 10ms, Zero Dependencies)"]
        LocalLLM["Local Open-Weight LLM (Optional)\n(Ollama / llama.cpp / Qwen 2.5)"]
        Addressed["Addressed-to-Me Vocative Detector"]
        QuickRep["Contextual Response Cards"]
        Catchup["What Did I Miss? 60-90s Recap"]
    end

    subgraph LocalStorage ["100% Local Storage & Personalization"]
        SQLite[("Local SQLite Database\n(hearth.db)")]
        Profiles["Local Profiles\n(default, family, work, clinic)"]
        Packs["Air-Gapped Language Packs\n(en, es, hi, de, fr)"]
    end

    %% Audio & Telemetry Flow
    Worklet -->|Binary Frames: 8B t_capture + PCM16| WS
    WS --> ASRWorker
    ASRWorker --> LocalAgree
    LocalAgree -->|Committed Words & Tentative Tail| WS
    LocalAgree -.->|Committed Clauses| MTWorker
    MTWorker -.->|Committed & Tentative Translation| WS
    ASRWorker -.->|Spectral Frames| DiarWorker
    DiarWorker -.->|Speaker Label| WS
    WS -->|streaming_update & final events| Display
    WS -->|t_capture echo & latency breakdown| Hud
    WS -->|Inverted Two-Way Dialogue| ConvSplit

    %% Async Layer Flow
    WS -.->|Completed Utterance (Background Task)| Addressed
    WS -.->|Completed Utterance (Background Task)| QuickRep
    Addressed -.-> RuleLLM
    QuickRep -.-> RuleLLM
    RuleLLM -.-> LocalLLM

    %% Storage & Configuration Flow
    Profiles -.->|Dynamic Prompt Biasing| ASRWorker
    Profiles -.->|Protected Terminology| MTWorker
    Packs -.->|Offline Models| MTWorker
    WS -->|Transcripts & Actionable Reminders| SQLite
```

---

## 2. The Streaming Engine & Latency Design

### Principle: The Caption Path Never Waits on an LLM or Utterance End
Traditional speech recognition systems wait for a VAD silence endpoint (usually 500–1,000 ms of silence) and then decode the entire 4–10 second utterance in a single batch. On multi-core CPUs, this causes a catastrophic 12–16 second latency spike.

Hearth re-architects speech transcription and translation as a continuous streaming pipeline:

1. **Hardware Timestamp Tracking (`t_capture`)**:
   - `pcm-recorder-processor.js` (running in an isolated `AudioWorkletGlobalScope`) prepends an 8-byte little-endian IEEE-754 Float64 timestamp to every 40 ms PCM chunk before sending it over the WebSocket.
   - Every server-emitted message echoes `t_capture`, allowing both client and backend to measure true end-to-end "spoken-to-displayed" latency down to the millisecond.

2. **LocalAgreement Prefix Commitment**:
   - `StreamingASREngine` evaluates rolling audio slices (250 ms step) with greedy decoding (`beam_size=1`) and word-level timestamps.
   - When adjacent hypotheses agree on words, the matching prefix is permanently committed (`is_committed=True`), and the audio buffer is trimmed up to the last committed word boundary with a 200 ms acoustic context overlap.
   - Tentative uncommitted words are displayed on screen with 55% opacity and an 80 ms fade-in transition. Committed words remain rock solid, preventing eye-straining flicker.

3. **Multi-Core Thread Isolation**:
   - High-core CPUs (e.g. 32 logical cores) trigger severe OpenMP thrashing if CTranslate2 is unconstrained (`intra_threads=0`), causing 13x latency explosions.
   - Hearth explicitly clamps CTranslate2 to `cpu_threads=4`, decoupling ASR inference into dedicated thread pools while the asyncio event loop routes network messages without stalling.

4. **Clause-Level Streaming Translation**:
   - As source words commit, `StreamingTranslator` translates punctuated clauses or semantic boundaries asynchronously without waiting for speaker turn completion.
   - Translation lines trail committed source text by $\le 400$ ms.

---

## 3. The 5 Operating Modes

1. **Captions Mode**: High-contrast, large-type live transcription in the speaker's language with live vocative and speaker indicators.
2. **Listening Mode**: Live source speech displayed alongside real-time subtitle translation (e.g., Spanish $\rightarrow$ English, Hindi $\rightarrow$ English).
3. **Conversation Mode**: 180° inverted split-screen table interface allowing two people sitting across a table to speak their own languages, with each person's side right-side-up from their perspective.
4. **Text-Only Mode**: Completely silent visual stream for quiet clinics, libraries, or noisy dining halls.
5. **Custom Mode**: User-configurable layout, font scales (18–46px), dyslexia-friendly glyphs (Lexend / OpenDyslexic), and haptic alerts.

---

## 4. Personalization without Identity Leakage

Personalization is completely local and structured around **Profiles**:
- `profiles/default.yaml`: General conversational speech.
- `profiles/family.yaml`: Kinship terms, family names, and home recipes.
- `profiles/work.yaml`: Engineering and technical project jargon.
- `profiles/clinic.yaml`: Medical terminology, medication dosages, and appointment logs.

When a profile is activated, its terminology is automatically injected into Whisper's prompt biasing buffer (`initial_prompt`) and protected against erroneous literal translation during machine translation.
