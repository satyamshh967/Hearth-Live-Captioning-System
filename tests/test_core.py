import pytest
import numpy as np
from services.core.config import load_config
from services.core.store.lexicon import LexiconStore, soundex
from services.core.store.sessions import SessionStore
from services.core.asr.post_processor import LexiconPostProcessor
from services.core.asr.mock_provider import MockASRProvider
from services.core.diar.lightweight_centroid import LightweightCentroidDiarizer
from services.core.config import DiarizationConfig
from services.core.llm.rule_fallback import RuleBasedLLMFallback


def test_config_loading():
    cfg = load_config("tiny")
    assert cfg.profile == "tiny"
    assert cfg.asr.model_size == "tiny"
    assert "dadaji" in cfg.friend_nicknames

    cfg_b = load_config("balanced")
    assert cfg_b.profile == "balanced"
    assert cfg_b.asr.model_size == "base"


def test_lexicon_and_soundex(tmp_path):
    db_file = str(tmp_path / "test_lex.db")
    store = LexiconStore(db_path=db_file)
    
    # Soundex check
    assert soundex("Dadaji") == "D320"
    assert soundex("Metformin") == "M316"
    assert soundex("Ramesh") == "R520"

    items = store.get_all()
    assert len(items) >= 30

    # Add custom word
    store.add_or_update("Gulab Jamun", category="food")
    match = store.find_best_match("gulab jamun")
    assert match is not None
    assert match[0] == "Gulab Jamun"

    # Corrections recording
    store.record_correction("met form in", "Metformin", "take tablet")
    corrections = store.get_corrections()
    assert len(corrections) == 1
    assert corrections[0]["corrected"] == "Metformin"


def test_post_processor(tmp_path):
    db_file = str(tmp_path / "test_post.db")
    store = LexiconStore(db_path=db_file)
    processor = LexiconPostProcessor(store)

    # Test single-word fuzzy correction
    corrected, _ = processor.correct_text("Did you take your matt forman today?")
    assert "Metformin" in corrected

    # Test Hindi family name fuzzy correction
    corrected_dadaji, _ = processor.correct_text("Please ask data g to come here.")
    assert "Dadaji" in corrected_dadaji

    # Test 2-word n-gram food term
    corrected_food, _ = processor.correct_text("We prepared dal makhny and roti.")
    assert "Dal makhani" in corrected_food


def test_session_store_and_privacy(tmp_path):
    db_file = str(tmp_path / "test_sess.db")
    store = SessionStore(db_path=db_file)

    s_id = store.create_session("Dinner with Priya & Rohan")
    store.append_utterance(s_id, "u1", "Priya", "Dadaji, did you take medicine?", lang="en", confidence=0.98)
    store.append_utterance(s_id, "u2", "Dadaji", "Haan beta, le li thi.", lang="hi", confidence=0.95)
    
    mem_id = store.add_memory(s_id, "medicine", "Evening dose", "Metformin taken before food", "7:30 PM")
    assert mem_id > 0
    assert store.toggle_memory_confirmation(mem_id) is True

    # Speaker renaming
    store.rename_speaker("Speaker 1", "Priya")
    names = store.get_speaker_names()
    assert names.get("Speaker 1") == "Priya"

    # Export formats
    md = store.export_markdown(s_id)
    assert "Dinner with Priya & Rohan" in md
    assert "Evening dose" in md

    ics = store.export_ics(s_id)
    assert "BEGIN:VCALENDAR" in ics
    assert "Evening dose" in ics

    # Privacy proof: Delete everything
    store.delete_everything()
    assert len(store.list_sessions()) == 0


def test_diarization_clustering():
    cfg = DiarizationConfig(min_speakers=1, max_speakers=4, similarity_threshold=0.65)
    diarizer = LightweightCentroidDiarizer(cfg)

    # Synthetic audio signals (different frequency contents)
    t = np.linspace(0, 1.0, 16000, dtype=np.float32)
    sig1 = np.sin(2 * np.pi * 200 * t) # Low pitch speaker (e.g., Dadaji)
    sig2 = np.sin(2 * np.pi * 500 * t) # Higher pitch speaker (e.g., Priya)

    res1 = diarizer.assign_speaker(sig1)
    assert res1.speaker_id == "Speaker 1"

    # Repeat sig1 -> should match Speaker 1
    res1_again = diarizer.assign_speaker(sig1)
    assert res1_again.speaker_id == "Speaker 1"

    # sig2 -> should create Speaker 2
    res2 = diarizer.assign_speaker(sig2)
    assert res2.speaker_id == "Speaker 2"

    # Rename
    diarizer.rename_speaker("Speaker 1", "Dadaji")
    assert diarizer.get_speakers()["Speaker 1"] == "Dadaji"


@pytest.mark.asyncio
async def test_rule_based_llm_intelligence():
    llm = RuleBasedLLMFallback()
    user_names = ["Dadaji", "Dada", "Ramesh", "Uncle"]

    # 1. Addressed to me: Direct question / imperative
    alert_direct = await llm.check_addressed_to_me("Dadaji, aap chai piyenge?", user_names)
    assert alert_direct.addressed_to_user is True
    assert alert_direct.user_vocative_used == "Dadaji"

    # Addressed to me: English vocative
    alert_direct_en = await llm.check_addressed_to_me("Listen Dadaji, did you check your sugar?", user_names)
    assert alert_direct_en.addressed_to_user is True

    # 3rd-person narration: NOT addressed to me
    alert_third = await llm.check_addressed_to_me("Dadaji went for a walk with Rohan this morning.", user_names)
    assert alert_third.addressed_to_user is False

    # 2. Question detection and quick replies
    qr = await llm.detect_question_and_replies("Dadaji, aap thodi aur dal lenge?", "Dadaji", "warm")
    assert qr.is_question is True
    assert len(qr.replies) == 3
    assert any("Haan" in r.text or "thodi" in r.text for r in qr.replies)

    # 3. Plain language simplification
    pl = await llm.simplify_plain_language("The doctor noted bilateral sensorineural presbycusis and hypertension.")
    assert "Age-related hearing change" in pl.plain_text or "hearing" in pl.plain_text.lower()
    assert len(pl.key_terms_explained) >= 1

    # 4. Things to remember extraction
    history = [
        {"speaker": "Doctor Verma", "text": "Rameshji, continue taking Metformin 500mg daily. We will meet next Thursday."},
        {"speaker": "Priya", "text": "Okay doctor, I will set a reminder."}
    ]
    memories = await llm.extract_memories(history)
    assert len(memories) >= 1
    assert any("Metformin" in m.title for m in memories)
