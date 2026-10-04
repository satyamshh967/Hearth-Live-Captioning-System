# Hearth — Privacy & Security Architecture

Hearth is built on an uncompromising privacy promise: **Family conversations and medical appointments belong to the family. Zero bytes leave your device.**

---

## 1. Zero Cloud Calls & Zero Telemetry Proof

Unlike cloud captioning services that continuously stream personal conversation audio to third-party tech company infrastructure, Hearth guarantees 100% on-device processing.

- **No Cloud Telemetry**: Zero Google Analytics, PostHog, Mixpanel, Sentry, or cloud logging.
- **No Third-Party ASR APIs**: Speech is decoded directly by a local, open-weight CTranslate2 Whisper model running on the host CPU or local GPU.
- **Audio Never Persisted to Disk**: Audio frames are processed entirely in memory as rolling Int16 buffers and purged immediately once an utterance transcription is complete.
- **Audio-Free Speaker Profiles**: Speaker clustering tracks only mathematical spectral centroids (128-dimensional feature vectors). No voice prints or raw recordings are preserved.

---

## 2. Programmatic Verification

Hearth includes an automated verification endpoint (`GET /api/privacy/verify-offline`) that confirms the local execution state:
```json
{
  "local_only": true,
  "cloud_telemetry_disabled": true,
  "asr_provider": "faster_whisper",
  "asr_device": "cpu",
  "diarization_local": true,
  "network_call_count": 0,
  "retention_days": 7
}
```

### Automated Offline Sandbox Test (`tests/test_offline_privacy.py`)
To prove that Hearth cannot send data externally, our test suite runs in a network-sandboxed environment where all outbound socket connections to non-loopback addresses trigger an immediate `IOError`:
```python
def guarded_connect(self, address):
    host = address[0]
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise IOError(f"PRIVACY VIOLATION: Blocked attempt to connect to external host: {host}")
    return original_connect(self, address)
```
The entire test suite passes cleanly with zero violations.

---

## 3. Data Retention & Permanent Deletion

1. **Auto-Purge**: All transcripts and session memories stored in the local SQLite database (`hearth.db`) are automatically cleaned up after a configurable retention window (default: 7 days).
2. **One-Tap "Delete Everything"**: The user can press the *Delete Everything* button in the privacy settings at any time (`POST /api/privacy/delete-all`), which immediately truncates all tables and purges all conversation history.
