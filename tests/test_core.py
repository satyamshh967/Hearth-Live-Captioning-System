import pytest
import time
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
    assert "listener" in cfg.friend_nicknames

    cfg_b = load_config("balanced")
    assert cfg_b.profile == "balanced"
    assert cfg_b.asr.model_size == "base"
    assert cfg_b.asr.cpu_threads == 4


def test_lexicon_and_soundex(tmp_path):
    db_file = str(tmp_path / "test_lex.db")
    store = LexiconStore(db_path=db_file)
    
    # Soundex check
    assert soundex("Dadaji") == "D320"
    assert soundex("Metformin") == "M316"
    assert soundex("Ramesh") == "R520"

    items = store.get_all()
    assert len(items) >= 20

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
    store.load_profile_vocabulary(["Metformin", "Dadaji", "Dal makhani", "Roti"])
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

    s_id = store.create_session("Dinner with Family")
    store.append_utterance(s_id, "u1", "Speaker 1", "Did you take your medicine?", translation="¿Tomaste tu medicina?", lang="en", confidence=0.98)
    store.append_utterance(s_id, "u2", "Speaker 2", "Yes, I took it before dinner.", translation="Sí, la tomé antes de cenar.", lang="en", confidence=0.95)
    
    mem_id = store.add_memory(s_id, "medicine", "Evening dose", "Metformin taken before food", "7:30 PM")
    assert mem_id > 0
    assert store.toggle_memory_confirmation(mem_id) is True

    # Speaker renaming
    store.rename_speaker("Speaker 1", "Alex")
    names = store.get_speaker_names()
    assert names.get("Speaker 1") == "Alex"

    # Export formats
    md = store.export_markdown(s_id)
    assert "Dinner with Family" in md
    assert "Evening dose" in md
    assert "¿Tomaste tu medicina?" in md

    srt = store.export_srt(s_id)
    assert "00:00:00,000 -->" in srt
    assert "Alex: Did you take your medicine?" in srt
    assert "¿Tomaste tu medicina?" in srt

    vtt = store.export_vtt(s_id)
    assert "WEBVTT - Hearth Live Transcript" in vtt
    assert "<v Alex>Did you take your medicine?" in vtt
    assert "<i>¿Tomaste tu medicina?</i>" in vtt

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


def test_profile_manager(tmp_path):
    from services.core.profiles.profile_manager import ProfileManager
    pm = ProfileManager(profiles_dir=str(tmp_path / "profiles"))
    profiles = pm.list_profiles()
    assert len(profiles) >= 4
    assert any(p["id"] == "family" for p in profiles)
    assert any(p["id"] == "clinic" for p in profiles)
    assert pm.set_active_profile("clinic") is True
    active = pm.get_active_profile()
    assert active.id == "clinic"
    assert "Metformin" in active.vocabulary

    # Terminology protection test
    text = "Please take Metformin 500mg before dinner."
    protected_text, placeholders = active.protect_terms_in_text(text)
    assert "__TERM_" in protected_text
    assert "Metformin" not in protected_text
    restored = active.restore_protected_terms(protected_text, placeholders)
    assert restored == text


def test_streaming_translator():
    from services.core.translation.streaming_translator import StreamingTranslator
    translator = StreamingTranslator()

    # Spanish translation test
    es_trans = translator.translate_text("hello", "en", "es")
    assert "hola" in es_trans.lower()

    # Hindi translation test
    hi_trans = translator.translate_text("water", "en", "hi")
    assert "पानी" in hi_trans

    # Clause segmentation triggers
    assert translator.should_translate_clause("Hello how are you?", 0.0) is True
    assert translator.should_translate_clause("One two three four five six", 0.0) is True
    assert translator.should_translate_clause("one two", time.time()) is False


def test_language_pack_manager(tmp_path):
    from services.core.packs.manager import LanguagePackManager
    lpm = LanguagePackManager(packs_dir=str(tmp_path / "packs"))
    packs = lpm.list_packs()
    assert len(packs) >= 3
    installed = [p for p in packs if p["is_installed"]]
    assert len(installed) >= 1
    langs = lpm.get_installed_languages()
    assert "en" in langs

