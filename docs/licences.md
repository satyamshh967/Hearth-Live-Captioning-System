# Open-Source Licenses & Model Provenance

All models, frameworks, and weights bundled in Hearth are verified open-source, commercially permissive (MIT, Apache-2.0, BSD-3, CC-BY-4.0). **Zero non-commercial-only (CC-BY-NC) or gated weights are used.**

---

## 1. Core Frameworks & Inference Engines

| Component | Repository / Author | License | Permissible Use |
|---|---|---|---|
| **CTranslate2** | [OpenNMT/CTranslate2](https://github.com/OpenNMT/CTranslate2) | **MIT** | Free commercial and personal offline use |
| **faster-whisper** | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | **MIT** | Free commercial and personal offline use |
| **sherpa-onnx** | [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) | **Apache-2.0** | Free commercial and personal offline use |
| **FastAPI** | [tiangolo/fastapi](https://github.com/tiangolo/fastapi) | **MIT** | Free commercial and personal use |
| **Uvicorn** | [encode/uvicorn](https://github.com/encode/uvicorn) | **BSD-3-Clause** | Free commercial and personal use |
| **RapidFuzz** | [maxbachmann/RapidFuzz](https://github.com/maxbachmann/RapidFuzz) | **MIT** | Free commercial and personal use |
| **WebSockets** | [python-websockets](https://github.com/python-websockets/websockets) | **BSD-3-Clause** | Free commercial and personal use |

---

## 2. ASR & Speech Models

| Model | Weights Provider | License | Hardware Profile |
|---|---|---|---|
| **Whisper Tiny (int8)** | OpenAI / Systran | **MIT** | Fast Profile (Raspberry Pi / Mobile / Low CPU) |
| **Whisper Base (int8)** | OpenAI / Systran | **MIT** | Balanced Profile (Standard Laptop / Desktop CPU) |
| **Whisper Small (int8)** | OpenAI / Systran | **MIT** | Accurate Profile (High-performance Multi-core CPU) |
| **Zipformer Transducer** | k2-fsa (sherpa-onnx) | **Apache-2.0** | Fast Monolingual Streaming Profile |

---

## 3. Machine Translation (MT) Models

| Language Pair | Architecture / Model | License | Offline Provenance |
|---|---|---|---|
| **Any $\rightarrow$ English** | Whisper Direct Translation | **MIT** | Built into CTranslate2 Whisper engine |
| **English $\leftrightarrow$ Spanish** | OPUS-MT (Helsinki-NLP) | **CC-BY-4.0 / Apache-2.0** | Helsinki-NLP Marian CTranslate2 quantized weights |
| **English $\leftrightarrow$ Hindi** | IndicTrans2 (AI4Bharat) | **MIT** | AI4Bharat open multilingual Indian MT |
| **English $\leftrightarrow$ French** | OPUS-MT (Helsinki-NLP) | **CC-BY-4.0 / Apache-2.0** | Helsinki-NLP Marian CTranslate2 quantized weights |
| **English $\leftrightarrow$ German** | OPUS-MT (Helsinki-NLP) | **CC-BY-4.0 / Apache-2.0** | Helsinki-NLP Marian CTranslate2 quantized weights |

---

## 4. Frontend & User Interface

| Dependency | License |
|---|---|
| **React 18 & React DOM** | **MIT** |
| **Vite** | **MIT** |
| **Tailwind CSS** | **MIT** |
| **Lucide Icons** | **ISC** (Permissive MIT equivalent) |
| **Atkinson Hyperlegible Font** | **OFL-1.1** (Open Font License) |
| **Inter Font** | **OFL-1.1** (Open Font License) |

---

## 5. Air-Gapped & Offline Verification

All weights and licenses can be inspected and verified offline directly within the `packs/` directory via `manifest.json`. No proprietary telemetry, authentication keys, or remote API tokens are required.
