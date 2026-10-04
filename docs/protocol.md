# Hearth WebSocket Protocol Specification (v1.0.0)

This document formalizes the real-time bidirectional WebSocket protocol between Hearth client display/microphone devices and the Hearth core server.

---

## 1. Connection Endpoint

```
ws://<HOST>:<PORT>/ws?room=<ROOM_ID>&role=<ROLE>
```

- **`room`** (string): Unique pairing identifier (e.g., `TABLE-4821`). All clients connected to the same room code share audio and receive synchronized captions.
- **`role`** (string):
  - `all`: Standard mode (device acts as both microphone and caption display).
  - `mic`: Microphone-only device (e.g. smartphone placed in the center of the dining table).
  - `display`: Display-only device (e.g. tablet propped up in front of Dadaji or TV).

---

## 2. Client -> Server Messages

### 2.1 Audio Frames (Binary)
- **Format**: Raw Int16 PCM mono audio samples at 16,000 Hz (Little Endian, 2 bytes per sample).
- **Frequency**: Transmitted continuously during active speech in chunks of 1024–4096 samples (~64–256 ms).

### 2.2 Text / JSON Messages

#### Rename Speaker
Updates a speaker cluster identifier to a real family member name across all connected displays and past session logs:
```json
{
  "type": "rename_speaker",
  "speaker_id": "Speaker 2",
  "new_name": "Priya"
}
```

#### Correct Word ("Correct-to-Learn Loop")
Registers a user correction from tapping an imperfect word on screen:
```json
{
  "type": "correct_word",
  "original": "matt forman",
  "corrected": "Metformin",
  "context": "did you take your matt forman today"
}
```

#### Catch-up Request ("What Did I Miss?")
Requests a 2-sentence conversational summary of the last 60–90 seconds:
```json
{
  "type": "catchup"
}
```

#### Request Plain Language Simplification
Translates medical/complex captions into everyday language for doctor visit mode:
```json
{
  "type": "request_plain_language",
  "utt_id": "8f3b2a1c",
  "text": "The patient presents with bilateral sensorineural presbycusis and postprandial hyperglycemia."
}
```

---

## 3. Server -> Client Messages

#### 3.1 Status
Sent upon connection or profile/speaker map changes:
```json
{
  "type": "status",
  "latency_ms": 989.5,
  "profile": "balanced",
  "model": "base",
  "room_id": "TABLE-4821",
  "session_id": "a1b2c3d4",
  "speakers": {
    "Speaker 1": "Dadaji",
    "Speaker 2": "Priya"
  }
}
```

#### 3.2 Partial Caption
Rolling streaming preview while a family member is speaking:
```json
{
  "type": "partial",
  "utt_id": "c4d5e6f7",
  "text": "Priya is coming for dinner",
  "lang": "en"
}
```

#### 3.3 Final Caption
Emitted when an utterance ends:
```json
{
  "type": "final",
  "utt_id": "c4d5e6f7",
  "speaker": "Rohan",
  "speaker_id": "Speaker 3",
  "text": "Priya is coming for dinner, shall we prepare dal makhani?",
  "lang": "en",
  "start": 0.0,
  "end": 4.51,
  "latency_ms": 996.0,
  "words": [
    {"w": "Priya", "conf": 0.98},
    {"w": "is", "conf": 0.99},
    {"w": "coming", "conf": 0.97},
    {"w": "for", "conf": 0.99},
    {"w": "dinner,", "conf": 0.98},
    {"w": "shall", "conf": 0.96},
    {"w": "we", "conf": 0.99},
    {"w": "prepare", "conf": 0.95},
    {"w": "dal", "conf": 0.97},
    {"w": "makhani?", "conf": 0.99}
  ]
}
```

#### 3.4 Addressed-to-Me Alert
Emitted when the speech directly addresses the target user:
```json
{
  "type": "alert",
  "kind": "name",
  "utt_id": "c4d5e6f7",
  "vocative": "Dadaji",
  "urgency": "high",
  "reasoning": "Direct question asking Dadaji for preference."
}
```

#### 3.5 Quick Replies Suggestions
Emitted when a conversational question is directed at Dadaji:
```json
{
  "type": "suggestions",
  "utt_id": "c4d5e6f7",
  "replies": [
    {"label": "Yes, a little", "text": "Haan beta, bas thodi si de do."},
    {"label": "No, full", "text": "Nahin beta, mera pet bhar gaya hai, shukriya."},
    {"label": "Later please", "text": "Thoda baad mein lena, abhi theek hai."}
  ]
}
```

#### 3.6 Catch-up Recap
Response to the "What did I miss?" button:
```json
{
  "type": "recap",
  "text": "Priya shared that Dr. Verma reviewed Dadaji's blood sugar reports and confirmed fasting is 118. Sunita and Rohan agreed to keep dinner light tonight.",
  "topic": "Doctor Verma's review of Dadaji's blood sugar",
  "speakers": ["Priya", "Sunita", "Rohan"]
}
```
