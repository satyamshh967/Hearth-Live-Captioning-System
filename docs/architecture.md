# Hearth — Architecture & Technical Design

Hearth is an offline-first, private live captioning system designed for Ramesh ("Dadaji"), a 76-year-old grandfather experiencing age-related bilateral hearing loss in lively, multi-speaker family dinner environments.

---

## 1. Core Architecture Diagram

```mermaid
flowchart TD
    subgraph Client ["Client Layer (Apps/Web PWA)"]
        Mic["Microphone Capture\n(AudioWorkletNode 16kHz PCM16)"]
        UI["Caption Display\n(Speaker-Colored Bubbles, Large Type)"]
        Alert["Addressed-to-Me Banner\n(Chime & Haptic Double-Pulse)"]
        QR["Table-Mic QR Code Relay\n(Phone Mic -> Tablet Display)"]
    end

    subgraph CriticalPath ["Critical Real-Time Path (< 2s Latency)"]
        WS["FastAPI WebSocket Server\n(/ws?room=TABLE-4821)"]
        VAD["Silero VAD / Energy Gate\n(Silence & Chunk Boundary)"]
        ASR["faster-whisper ASR\n(CTranslate2 int8 CPU/GPU)"]
        PostProc["Lexicon Post-Processor\n(Rapidfuzz + Soundex Phonetics)"]
        Diar["Lightweight Centroid Diarizer\n(128-dim Spectral Embeddings)"]
    end

    subgraph AsyncIntelligence ["Asynchronous Intelligence (Non-Blocking)"]
        RuleLLM["Rule-Based Fallback Engine\n(Sub-5ms, Deterministic)"]
        LocalLLM["Local Open-Weight LLM\n(Ollama / llama.cpp / Qwen 2.5)"]
        Addressed["Addressed-to-Me Detector"]
        QuickRep["3 Quick Replies in Dadaji's Voice"]
        Recap["What Did I Miss? 60-90s Recap"]
        DoctorMode["Plain-Language Medical Simplifier"]
    end

    subgraph Storage ["Local Storage (100% On-Device)"]
        SQLite[("Local SQLite Database\n(hearth.db)")]
        LexiconTable["Personal Lexicon & Corrections"]
        SessionTable["Transcripts & Actionable Memories"]
    end

    %% Audio Flow
    Mic -->|Binary PCM16 Frames| WS
    WS --> VAD
    VAD -->|Active Speech Buffer| ASR
    ASR -->|Raw Hypotheses| PostProc
    PostProc -->|Cleaned Text| WS
    VAD -->|Audio Features| Diar
    Diar -->|Speaker Label| WS
    WS -->|Partial & Final Captions| UI

    %% Async Layer Flow
    PostProc -.->|Completed Utterance| Addressed
    PostProc -.->|Completed Utterance| QuickRep
    Addressed -.->|Rule / Open LLM| RuleLLM
    QuickRep -.->|Rule / Open LLM| RuleLLM
    RuleLLM -.->|Optional Local Host| LocalLLM

    Addressed -->|Name Alert| Alert
    QuickRep -->|3 Reply Chips| UI
    UI -->|What Did I Miss?| Recap
    Recap -->|2-Sentence Summary| UI
    UI -->|Plain Language Toggle| DoctorMode

    %% Storage connections
    PostProc <-->|Biasing Words & Corrections| LexiconTable
    WS -->|Save Utterance & Memories| SessionTable
    LexiconTable --- SQLite
    SessionTable --- SQLite
```

---

## 2. Decoupled Pipeline Design

### Principle: The Real-Time Caption Path Never Waits on an LLM
The primary failure mode of assistive speech tools is latency drift. If audio transcribing waits on an LLM completion, speech lags by 3–6 seconds, making conversational banter impossible for Dadaji to follow.

1. **Streaming Audio -> Screen (< 2s)**:
   - Microphone samples are captured via `AudioWorkletNode` in 16 kHz 16-bit mono PCM.
   - Streamed over WebSocket to FastAPI.
   - Silero VAD monitors energy envelopes. Rolling partials are emitted every 700ms.
   - At utterance boundaries (350ms silence or 8s limit), `faster-whisper` transcribes the chunk.
   - `LexiconPostProcessor` applies Rapidfuzz token matching and Soundex phonetic verification against Dadaji's 40+ personalized family words.
   - The final caption is broadcast to all room display devices immediately.

2. **Asynchronous Intelligence Layer**:
   - Once the final caption is emitted to the screen, concurrent background tasks evaluate:
     - **Addressed-to-Me Check**: Distinguishes between direct imperatives (*"Dadaji, did you take your medicine?"*) vs third-person family narration (*"Dadaji went for a walk"*).
     - **Question Detection**: Triggers 3 contextual quick reply buttons in Dadaji's calm, polite Hinglish tone.
     - **Memory Extraction**: Extracts medication reminders and clinic follow-ups as confirmable chips.

3. **Graceful Rule-Based Degradation**:
   - If an open-weight local LLM (e.g., Ollama `qwen2.5:3b`) is unreachable or exceeds a 3.0-second timeout, Hearth instantly switches to `RuleBasedLLMFallback` without dropping frames.
