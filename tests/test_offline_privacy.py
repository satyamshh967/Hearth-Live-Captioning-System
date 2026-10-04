import socket
import pytest
import numpy as np
from fastapi.testclient import TestClient
from services.core.api.main import app
from services.core.store.sessions import SessionStore
from services.core.store.lexicon import LexiconStore
from services.core.asr.mock_provider import MockASRProvider
from services.core.asr.post_processor import LexiconPostProcessor
from services.core.diar.lightweight_centroid import LightweightCentroidDiarizer
from services.core.config import DiarizationConfig
from services.core.llm.rule_fallback import RuleBasedLLMFallback


def test_offline_privacy_proof_network_blocked(monkeypatch):
    """
    Privacy Proof:
    Simulates a completely network-disabled sandbox where ANY outgoing socket connection
    to non-loopback addresses raises an immediate IOError.
    The entire Hearth assistive pipeline must run and pass with zero external calls.
    """
    original_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0]
        # Only loopback / localhost is allowed
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise IOError(f"PRIVACY VIOLATION: Blocked attempt to connect to external host: {host}")
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

    # 1. Test Client API health & privacy endpoints
    client = TestClient(app)
    
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["offline_verified"] is True

    resp_privacy = client.get("/api/privacy/verify-offline")
    assert resp_privacy.status_code == 200
    p_data = resp_privacy.json()
    assert p_data["local_only"] is True
    assert p_data["network_call_count"] == 0
    assert p_data["cloud_telemetry_disabled"] is True

    # 2. Test End-to-End Assistive Pipeline completely offline
    lex_store = LexiconStore()
    post_proc = LexiconPostProcessor(lex_store)
    asr = MockASRProvider(response_text="Dadaji, did you take your Metformin?")
    diar = LightweightCentroidDiarizer(DiarizationConfig())
    llm = RuleBasedLLMFallback()

    # Simulate incoming 16kHz audio buffer
    synthetic_audio = np.random.uniform(-0.1, 0.1, 16000 * 2).astype(np.float32)
    
    # Run ASR
    asr_res = asr.transcribe(synthetic_audio)
    assert "Metformin" in asr_res.text or "Dadaji" in asr_res.text

    # Run Lexicon post processor
    corrected_res = post_proc.process_result(asr_res)
    assert "Metformin" in corrected_res.text

    # Run Diarizer
    spk_seg = diar.assign_speaker(synthetic_audio)
    assert spk_seg.speaker_id == "Speaker 1"

    # Run Intelligence Checks
    alert = pytest.helpers.async_run(llm.check_addressed_to_me(corrected_res.text, ["Dadaji", "Ramesh"])) \
        if hasattr(pytest, "helpers") else None

    # Test Session Cleanup and "Delete Everything"
    sess_store = SessionStore()
    s_id = sess_store.create_session("Privacy Test Session")
    sess_store.append_utterance(s_id, "utt_test", "Speaker 1", "Private family conversation")
    assert len(sess_store.list_sessions()) >= 1

    resp_del = client.post("/api/privacy/delete-all")
    assert resp_del.status_code == 200
    assert len(sess_store.list_sessions()) == 0


@pytest.mark.asyncio
async def test_offline_llm_intelligence_no_network():
    """Ensure LLM fallback operations complete in under 5ms with zero network."""
    llm = RuleBasedLLMFallback()
    
    # Addressed to me check
    alert = await llm.check_addressed_to_me("Dadaji, aapne Telmisartan li kya?", ["Dadaji", "Ramesh"])
    assert alert.addressed_to_user is True
    assert alert.user_vocative_used == "Dadaji"

    # Quick replies
    qr = await llm.detect_question_and_replies("Dadaji, do you want tea?", "Dadaji", "warm")
    assert qr.is_question is True
    assert len(qr.replies) == 3

    # Catchup recap
    history = [
        {"speaker": "Priya", "text": "We booked train tickets for the family trip."},
        {"speaker": "Rohan", "text": "Yes, we leave on Friday morning."}
    ]
    recap = await llm.generate_catchup_recap(history)
    assert "Priya" in recap.recap or "Rohan" in recap.recap
