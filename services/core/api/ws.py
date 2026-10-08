"""
Hearth WebSocket Server
Routes real-time audio streams and events with sub-500ms streaming latency:
- Streaming LocalAgreement ASR engine (isolated compute threads, zero thread thrashing)
- Real-time clause streaming MT translation with terminology protection
- 5 operational modes (Captions, Listening, Conversation, Text Only, Custom)
- Asynchronous intelligence and ambient alerts
- Backpressure governor to prevent audio buffer latency growth
"""

import asyncio
import json
import logging
import struct
import time
import uuid
from typing import Dict, Set, Optional, List
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from ..config import HearthConfig
from ..asr.provider import ASRProvider, ASRResult
from ..asr.streaming_engine import StreamingASREngine, StreamingSession, StreamingHypothesis
from ..asr.post_processor import LexiconPostProcessor
from ..translation.streaming_translator import StreamingTranslator
from ..profiles.profile_manager import ProfileManager, Profile
from ..packs.manager import LanguagePackManager
from ..diar.provider import DiarizerProvider
from ..llm.provider import LLMProvider
from ..store.sessions import SessionStore
from ..store.lexicon import LexiconStore

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections grouped by room code."""
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.ws_to_room: Dict[WebSocket, str] = {}
        self.ws_to_role: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, room_id: str, role: str = "all"):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(websocket)
        self.ws_to_room[websocket] = room_id
        self.ws_to_role[websocket] = role
        logger.info(f"WebSocket connected: room={room_id}, role={role}, total={len(self.rooms[room_id])}")

    def disconnect(self, websocket: WebSocket):
        room_id = self.ws_to_room.get(websocket)
        if room_id and room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        self.ws_to_room.pop(websocket, None)
        self.ws_to_role.pop(websocket, None)
        logger.info(f"WebSocket disconnected: room={room_id}")

    async def broadcast(self, room_id: str, message: dict):
        if room_id not in self.rooms:
            return
        msg_json = json.dumps(message)
        dead = set()
        for ws in self.rooms[room_id]:
            try:
                await ws.send_text(msg_json)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)


class AudioSessionState:
    """Maintains state for a room's active streaming conversation."""
    def __init__(
        self,
        room_id: str,
        streaming_engine: StreamingASREngine,
        profile_manager: ProfileManager,
        config: HearthConfig
    ):
        self.room_id = room_id
        self.session_id = str(uuid.uuid4())[:8]
        self.current_utt_id = str(uuid.uuid4())[:8]

        # Mode and Language Pair
        self.mode: str = config.mode
        self.source_lang: str = config.source_language
        self.target_lang: str = config.target_language
        self.profile: Profile = profile_manager.get_active_profile()

        # Streaming Session
        self.streaming_session: StreamingSession = streaming_engine.create_session(
            initial_prompt=self.profile.get_prompt_biasing_string()
        )

        # Audio tracking & VAD
        self.audio_accumulator = bytearray()
        self.last_speech_time = time.time()
        self.speech_start_time = 0.0
        self.is_speaking = False
        self.is_processing_chunk = False

        self.first_capture_time: float = 0.0
        self.last_capture_time: float = 0.0
        self.last_translate_time: float = 0.0

        self.last_committed_source: str = ""
        self.last_committed_translated: str = ""
        self.active_speaker: str = "Speaker 1"
        self.recent_utterance_history: List[Dict] = []


class HearthWSServer:
    def __init__(
        self,
        config: HearthConfig,
        asr_provider: ASRProvider,
        post_processor: LexiconPostProcessor,
        diarizer: DiarizerProvider,
        llm_provider: LLMProvider,
        session_store: SessionStore,
        lexicon_store: LexiconStore,
        profile_manager: Optional[ProfileManager] = None,
        pack_manager: Optional[LanguagePackManager] = None,
        translator: Optional[StreamingTranslator] = None,
    ):
        self.config = config
        self.asr_provider = asr_provider
        self.post_processor = post_processor
        self.diarizer = diarizer
        self.llm_provider = llm_provider
        self.session_store = session_store
        self.lexicon_store = lexicon_store

        self.profile_manager = profile_manager or ProfileManager()
        self.pack_manager = pack_manager or LanguagePackManager()
        self.translator = translator or StreamingTranslator()

        # Isolated Streaming Engine
        self.streaming_engine = StreamingASREngine(
            model_size=config.asr.model_size,
            device=config.asr.device,
            compute_type=config.asr.compute_type,
            cpu_threads=config.asr.cpu_threads,
            step_duration_sec=config.asr.streaming_step_sec,
            initial_prompt=self.profile_manager.get_active_profile().get_prompt_biasing_string(),
            fallback_asr=self.asr_provider,
        )

        self.manager = ConnectionManager()
        self.states: Dict[str, AudioSessionState] = {}

    def get_or_create_state(self, room_id: str) -> AudioSessionState:
        if room_id not in self.states:
            self.states[room_id] = AudioSessionState(
                room_id=room_id,
                streaming_engine=self.streaming_engine,
                profile_manager=self.profile_manager,
                config=self.config
            )
        return self.states[room_id]

    async def handle_websocket(self, websocket: WebSocket, room_id: str = "default", role: str = "all"):
        await self.manager.connect(websocket, room_id, role)
        state = self.get_or_create_state(room_id)

        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "status",
            "latency_ms": 0.0,
            "profile": self.config.profile,
            "model": self.config.asr.model_size,
            "mode": state.mode,
            "source_lang": state.source_lang,
            "target_lang": state.target_lang,
            "active_profile": state.profile.name,
            "room_id": room_id,
            "session_id": state.session_id,
            "speakers": self.diarizer.get_speakers(),
        }))

        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message and message["bytes"]:
                    await self._process_audio_bytes(state, message["bytes"])
                elif "text" in message and message["text"]:
                    await self._process_json_message(websocket, state, message["text"])
        except WebSocketDisconnect:
            self.manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error in room {room_id}: {e}", exc_info=True)
            self.manager.disconnect(websocket)

    async def _process_json_message(self, websocket: WebSocket, state: AudioSessionState, text: str):
        try:
            data = json.loads(text)
        except Exception:
            return

        msg_type = data.get("type")

        if msg_type == "set_mode":
            mode = data.get("mode", "captions")
            state.mode = mode
            await self.manager.broadcast(state.room_id, {
                "type": "status",
                "mode": state.mode,
                "source_lang": state.source_lang,
                "target_lang": state.target_lang,
            })

        elif msg_type == "set_language_pair":
            state.source_lang = data.get("source_lang", state.source_lang)
            state.target_lang = data.get("target_lang", state.target_lang)
            await self.manager.broadcast(state.room_id, {
                "type": "status",
                "mode": state.mode,
                "source_lang": state.source_lang,
                "target_lang": state.target_lang,
            })

        elif msg_type == "set_task":
            task = data.get("task", "transcribe")
            if task == "translate":
                state.mode = "listening"
            else:
                state.mode = "captions"
            await self.manager.broadcast(state.room_id, {
                "type": "status",
                "task": task,
                "mode": state.mode,
            })

        elif msg_type == "set_profile":
            profile_id = data.get("profile_id", "default")
            if self.profile_manager.set_active_profile(profile_id):
                state.profile = self.profile_manager.get_active_profile()
                state.streaming_session.prompt = state.profile.get_prompt_biasing_string()
                await self.manager.broadcast(state.room_id, {
                    "type": "status",
                    "active_profile": state.profile.name,
                })

        elif msg_type == "rename_speaker":
            speaker_id = data.get("speaker_id")
            new_name = data.get("new_name")
            if speaker_id and new_name:
                self.diarizer.rename_speaker(speaker_id, new_name)
                self.session_store.rename_speaker(speaker_id, new_name)
                await self.manager.broadcast(state.room_id, {
                    "type": "status",
                    "speakers": self.diarizer.get_speakers(),
                })

        elif msg_type == "correct_word":
            orig = data.get("original", "")
            corr = data.get("corrected", "")
            ctx = data.get("context", "")
            if orig and corr:
                self.lexicon_store.record_correction(orig, corr, ctx)
                self.profile_manager.add_word_to_active_profile(corr)
                await websocket.send_text(json.dumps({
                    "type": "correction_saved",
                    "original": orig,
                    "corrected": corr,
                }))

        elif msg_type == "catchup":
            history = state.recent_utterance_history[-10:]
            recap_result = await self.llm_provider.generate_catchup_recap(history)
            await websocket.send_text(json.dumps({
                "type": "recap",
                "text": recap_result.recap,
                "topic": recap_result.key_topic,
                "speakers": recap_result.speakers_involved,
            }))

        elif msg_type == "request_plain_language":
            utt_id = data.get("utt_id")
            original_text = data.get("text", "")
            if original_text:
                simplified = await self.llm_provider.simplify_plain_language(original_text)
                await websocket.send_text(json.dumps({
                    "type": "plain_language",
                    "utt_id": utt_id,
                    "original": original_text,
                    "plain_text": simplified.plain_text,
                    "terms": simplified.key_terms_explained,
                }))

    async def _process_audio_bytes(self, state: AudioSessionState, raw_bytes: bytes):
        t_ws_recv = time.time()
        t_capture = t_ws_recv
        audio_payload = raw_bytes

        # Extract 8-byte Float64 t_capture header if present
        if len(raw_bytes) > 8:
            try:
                candidate_ts = struct.unpack("<d", raw_bytes[:8])[0]
                if 1577836800.0 < candidate_ts < 2524608000.0:
                    t_capture = candidate_ts
                    audio_payload = raw_bytes[8:]
            except Exception:
                pass

        state.last_capture_time = t_capture

        # Audio is 16kHz 16-bit mono PCM
        samples = np.frombuffer(audio_payload, dtype=np.int16).astype(np.float32) / 32768.0
        if len(samples) == 0:
            return

        # 1. ALWAYS add audio samples immediately into session buffer (never dropped!)
        state.streaming_session.add_audio_samples(samples, t_capture)

        rms = np.sqrt(np.mean((samples * 32768.0) ** 2))
        energy_threshold = 140.0  # sensitive to natural conversational speech

        now = time.time()
        if rms > energy_threshold:
            state.last_speech_time = now
            if not state.is_speaking:
                state.is_speaking = True
                state.speech_start_time = now
                state.first_capture_time = t_capture
                state.current_utt_id = str(uuid.uuid4())[:8]

        # 2. Trigger decode step if ready and worker is idle
        task = "translate" if (state.mode == "listening" and state.target_lang == "en") else "transcribe"
        lang = None if state.source_lang == "auto" else state.source_lang

        if not state.is_processing_chunk and state.streaming_session.can_decode():
            state.is_processing_chunk = True
            asyncio.create_task(
                self._run_streaming_step(state, t_capture=t_capture, task=task, language=lang)
            )

        # 3. Utterance endpoint check (silence duration >= 500ms)
        silence_duration = now - state.last_speech_time
        if state.is_speaking and silence_duration >= 0.50:
            state.is_speaking = False
            asyncio.create_task(self._run_endpoint_finalization(state))

    async def _run_streaming_step(
        self,
        state: AudioSessionState,
        t_capture: float,
        task: str,
        language: Optional[str]
    ):
        """Asynchronously runs a streaming decode step on worker thread pool."""
        try:
            t0 = time.time()
            hyp: Optional[StreamingHypothesis] = await asyncio.to_thread(
                state.streaming_session.decode_step,
                task=task,
                language=language,
            )

            if hyp and (hyp.committed_text or hyp.tentative_text):
                # Update speaker diarization dynamically if new audio accumulated
                if len(state.streaming_session.audio_buffer) >= 16000 * 0.5:
                    speaker_seg = await asyncio.to_thread(
                        self.diarizer.assign_speaker,
                        state.streaming_session.audio_buffer[-16000*2:]
                    )
                    state.active_speaker = speaker_seg.display_name

                # Translation path (if in translation mode and target is not English via task='translate')
                committed_trans = ""
                tentative_trans = ""
                if state.mode in ("listening", "conversation", "text_only"):
                    tgt = state.target_lang
                    src = "en" if state.source_lang == "auto" else state.source_lang
                    
                    if task == "translate":
                        # Direct Whisper speech-to-English translation
                        committed_trans = hyp.committed_text
                        tentative_trans = hyp.tentative_text
                    else:
                        if hyp.committed_text:
                            committed_trans = await asyncio.to_thread(
                                self.translator.translate_text,
                                hyp.committed_text,
                                src,
                                tgt,
                                profile=state.profile,
                                is_final=False,
                            )
                        if hyp.tentative_text:
                            tentative_trans = await asyncio.to_thread(
                                self.translator.translate_text,
                                hyp.tentative_text,
                                src,
                                tgt,
                                profile=state.profile,
                                is_final=False,
                            )

                state.last_committed_source = hyp.committed_text
                state.last_committed_translated = committed_trans

                total_spoken_to_partial = (time.time() - hyp.t_first_capture) * 1000

                # Broadcast live streaming update (solid committed words + ~55% opacity tentative tail)
                msg = {
                    "type": "streaming_update",
                    "utt_id": state.current_utt_id,
                    "committed_source": hyp.committed_text,
                    "tentative_source": hyp.tentative_text,
                    "committed_translated": committed_trans,
                    "tentative_translated": tentative_trans,
                    "speaker": state.active_speaker,
                    "source_lang": state.source_lang,
                    "target_lang": state.target_lang,
                    "mode": state.mode,
                    "t_capture": round(hyp.t_first_capture, 4),
                    "latency_breakdown": {
                        "asr_inference_ms": hyp.latency_breakdown.get("asr_inference_ms", 0.0),
                        "total_spoken_to_partial_ms": round(total_spoken_to_partial, 1),
                    }
                }
                await self.manager.broadcast(state.room_id, msg)

                # Also emit backward-compatible 'partial' event
                full_display_text = f"{hyp.committed_text} {hyp.tentative_text}".strip()
                await self.manager.broadcast(state.room_id, {
                    "type": "partial",
                    "utt_id": state.current_utt_id,
                    "text": full_display_text,
                    "lang": state.source_lang,
                })

        except Exception as e:
            logger.debug(f"Streaming step error: {e}")
        finally:
            state.is_processing_chunk = False
            # Self-pump: if more audio accumulated while decoding, immediately run next decode step
            if state.streaming_session.can_decode():
                state.is_processing_chunk = True
                asyncio.create_task(
                    self._run_streaming_step(state, t_capture=t_capture, task=task, language=language)
                )

    async def _run_endpoint_finalization(self, state: AudioSessionState):
        """Finalizes the utterance upon VAD endpoint (silence), refines translation, and persists."""
        try:
            # Await any in-flight streaming step so all spoken audio frames are fully transcribed
            wait_start = time.time()
            while state.is_processing_chunk and (time.time() - wait_start < 2.5):
                await asyncio.sleep(0.03)

            final_hyp: StreamingHypothesis = await asyncio.to_thread(state.streaming_session.finalize)
            full_text = final_hyp.committed_text.strip()
            if not full_text:
                return

            # Apply terminology & lexicon post-processor
            words_tokens = [
                {"w": w.word, "conf": w.confidence} for w in final_hyp.all_words
            ]

            # Refined translation pass
            refined_trans = ""
            if state.mode in ("listening", "conversation", "text_only"):
                src = "en" if state.source_lang == "auto" else state.source_lang
                tgt = state.target_lang
                refined_trans = await asyncio.to_thread(
                    self.translator.translate_text,
                    full_text,
                    src,
                    tgt,
                    profile=state.profile,
                    is_final=True,
                )

            total_latency = (time.time() - (final_hyp.t_first_capture or time.time())) * 1000

            # Emit final caption
            final_msg = {
                "type": "final",
                "utt_id": state.current_utt_id,
                "speaker": state.active_speaker,
                "text": full_text,
                "translated_text": refined_trans,
                "lang": state.source_lang,
                "task": "translate" if state.mode == "listening" else "transcribe",
                "start": 0.0,
                "end": round(len(full_text.split()) * 0.35, 2),
                "words": words_tokens,
                "latency_ms": round(total_latency, 1),
                "t_capture": round(final_hyp.t_first_capture, 4),
            }
            await self.manager.broadcast(state.room_id, final_msg)

            # Record in session history
            now = time.time()
            utt_record = {
                "speaker": state.active_speaker,
                "text": full_text,
                "translated_text": refined_trans,
                "utt_id": state.current_utt_id,
                "lang": state.source_lang,
                "time": now,
            }
            state.recent_utterance_history.append(utt_record)
            if len(state.recent_utterance_history) > 30:
                state.recent_utterance_history.pop(0)

            # Persist to SQLite in threadpool
            await asyncio.to_thread(
                self.session_store.append_utterance,
                session_id=state.session_id,
                utt_id=state.current_utt_id,
                speaker=state.active_speaker,
                text=full_text,
                translation=refined_trans if refined_trans else None,
                lang=state.source_lang,
                start_sec=0.0,
                end_sec=round(len(full_text.split()) * 0.35, 2),
                confidence=0.92,
            )

            # Trigger asynchronous intelligence checks
            asyncio.create_task(self._run_async_intelligence(state, state.current_utt_id, full_text))

        except Exception as e:
            logger.error(f"Error in endpoint finalization: {e}", exc_info=True)

    async def _run_async_intelligence(self, state: AudioSessionState, utt_id: str, text: str):
        """Asynchronous intelligence layer: Addressed-to-me alert & Quick replies."""
        try:
            # 1. Addressed alert check based on active profile triggers
            triggers = state.profile.vocative_triggers or ["hey", "listen", "user"]
            alert_res = await self.llm_provider.check_addressed_to_me(
                text=text,
                user_names=triggers
            )
            if alert_res.addressed_to_user:
                await self.manager.broadcast(state.room_id, {
                    "type": "alert",
                    "kind": "name",
                    "utt_id": utt_id,
                    "vocative": alert_res.user_vocative_used or "Direct address",
                    "urgency": alert_res.urgency,
                    "reasoning": alert_res.reasoning,
                })

            # 2. Question check & 3 quick replies
            question_res = await self.llm_provider.detect_question_and_replies(
                text=text,
                friend_name=state.profile.name,
                tone_profile="polite, concise"
            )
            if question_res.is_question and question_res.replies:
                await self.manager.broadcast(state.room_id, {
                    "type": "suggestions",
                    "utt_id": utt_id,
                    "replies": [{"label": r.label, "text": r.text} for r in question_res.replies],
                })
                if not alert_res.addressed_to_user and "?" in text:
                    await self.manager.broadcast(state.room_id, {
                        "type": "alert",
                        "kind": "question",
                        "utt_id": utt_id,
                    })

        except Exception as e:
            logger.error(f"Async intelligence error: {e}")
