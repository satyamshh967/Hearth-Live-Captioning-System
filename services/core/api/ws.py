import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Set, Optional, List
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from ..config import HearthConfig
from ..asr.provider import ASRProvider, ASRResult
from ..asr.post_processor import LexiconPostProcessor
from ..diar.provider import DiarizerProvider
from ..llm.provider import LLMProvider
from ..store.sessions import SessionStore
from ..store.lexicon import LexiconStore

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections grouped by room code."""
    def __init__(self):
        # room_id -> set of WebSockets
        self.rooms: Dict[str, Set[WebSocket]] = {}
        # ws -> room_id
        self.ws_to_room: Dict[WebSocket, str] = {}
        # ws -> role ("display", "mic", "all")
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
    """Tracks streaming audio buffer, VAD state, and active utterances for a room."""
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.audio_buffer = bytearray()
        self.current_utt_id = str(uuid.uuid4())[:8]
        self.session_id = str(uuid.uuid4())[:8]
        self.last_speech_time = time.time()
        self.last_partial_time = time.time()
        self.is_speaking = False
        self.speech_start_time = 0.0
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
    ):
        self.config = config
        self.asr_provider = asr_provider
        self.post_processor = post_processor
        self.diarizer = diarizer
        self.llm_provider = llm_provider
        self.session_store = session_store
        self.lexicon_store = lexicon_store
        self.manager = ConnectionManager()
        self.states: Dict[str, AudioSessionState] = {}

    def get_or_create_state(self, room_id: str) -> AudioSessionState:
        if room_id not in self.states:
            self.states[room_id] = AudioSessionState(room_id)
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
        if msg_type == "rename_speaker":
            speaker_id = data.get("speaker_id")
            new_name = data.get("new_name")
            if speaker_id and new_name:
                self.diarizer.rename_speaker(speaker_id, new_name)
                self.session_store.rename_speaker(speaker_id, new_name)
                # Broadcast update
                await self.manager.broadcast(state.room_id, {
                    "type": "status",
                    "latency_ms": 0.0,
                    "profile": self.config.profile,
                    "model": self.config.asr.model_size,
                    "speakers": self.diarizer.get_speakers(),
                })

        elif msg_type == "correct_word":
            orig = data.get("original", "")
            corr = data.get("corrected", "")
            ctx = data.get("context", "")
            if orig and corr:
                self.lexicon_store.record_correction(orig, corr, ctx)
                # Acknowledge correction
                await websocket.send_text(json.dumps({
                    "type": "correction_saved",
                    "original": orig,
                    "corrected": corr,
                }))

        elif msg_type == "catchup":
            # "What did I miss?" requested
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
        state.audio_buffer.extend(raw_bytes)
        
        # Audio is 16kHz 16-bit mono PCM: 2 bytes per sample -> 32000 bytes per second
        # Check energy level for VAD
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
        if len(samples) == 0:
            return

        rms = np.sqrt(np.mean(samples ** 2))
        energy_threshold = 400.0  # standard threshold for 16-bit PCM speech

        now = time.time()
        if rms > energy_threshold:
            state.last_speech_time = now
            if not state.is_speaking:
                state.is_speaking = True
                state.speech_start_time = now
                state.current_utt_id = str(uuid.uuid4())[:8]

        # Rolling partial transcription every 700ms while speaking
        min_bytes_for_partial = int(16000 * 2 * 0.8) # 0.8s
        if state.is_speaking and (now - state.last_partial_time > 0.7) and len(state.audio_buffer) >= min_bytes_for_partial:
            state.last_partial_time = now
            # Take last 2 seconds for rolling partial
            window_bytes = state.audio_buffer[-int(16000 * 2 * 2.0):]
            audio_f32 = np.frombuffer(window_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            try:
                partial_text = self.asr_provider.transcribe_stream(audio_f32)
                if partial_text:
                    await self.manager.broadcast(state.room_id, {
                        "type": "partial",
                        "utt_id": state.current_utt_id,
                        "text": partial_text,
                        "lang": "en",
                    })
            except Exception as e:
                logger.debug(f"Partial transcribe error: {e}")

        # Check utterance end condition:
        # Either silence duration > 400ms after speaking, or maximum duration (8 seconds) reached
        silence_duration = now - state.last_speech_time
        max_duration_reached = (len(state.audio_buffer) >= 16000 * 2 * 8.0)
        
        if (state.is_speaking and silence_duration >= 0.40) or max_duration_reached:
            # Utterance complete!
            state.is_speaking = False
            total_bytes = len(state.audio_buffer)
            if total_bytes < 16000 * 2 * 0.4: # Ignore extremely brief clicks (< 400ms)
                state.audio_buffer.clear()
                return

            audio_full = np.frombuffer(state.audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            state.audio_buffer.clear()

            # Execute transcription and diarization
            t_start = time.time()
            prompt = self.lexicon_store.get_prompt_biasing_string()
            result: ASRResult = self.asr_provider.transcribe(audio_full, initial_prompt=prompt)
            result = self.post_processor.process_result(result)
            speaker_seg = self.diarizer.assign_speaker(audio_full)

            # Skip empty hallucinations
            if not result.text.strip():
                return

            total_latency = (time.time() - t_start) * 1000

            # Broadcast final caption IMMEDIATELY (critical path sub-2s)
            final_msg = {
                "type": "final",
                "utt_id": state.current_utt_id,
                "speaker": speaker_seg.display_name,
                "speaker_id": speaker_seg.speaker_id,
                "text": result.text,
                "lang": result.language,
                "start": result.start,
                "end": result.end,
                "words": [{"w": w.word, "conf": w.confidence} for w in result.words],
                "latency_ms": round(total_latency, 1),
            }
            await self.manager.broadcast(state.room_id, final_msg)

            # Append to session history & SQLite
            utt_record = {
                "speaker": speaker_seg.display_name,
                "text": result.text,
                "utt_id": state.current_utt_id,
                "lang": result.language,
                "time": now,
            }
            state.recent_utterance_history.append(utt_record)
            if len(state.recent_utterance_history) > 30:
                state.recent_utterance_history.pop(0)

            self.session_store.append_utterance(
                session_id=state.session_id,
                utt_id=state.current_utt_id,
                speaker=speaker_seg.display_name,
                text=result.text,
                lang=result.language,
                start_sec=result.start,
                end_sec=result.end,
                confidence=float(np.mean([w.confidence for w in result.words])) if result.words else 0.9,
            )

            # Fire async intelligence checks concurrently (never blocks ASR)
            asyncio.create_task(self._run_async_intelligence(state, state.current_utt_id, result.text))

    async def _run_async_intelligence(self, state: AudioSessionState, utt_id: str, text: str):
        """Asynchronous intelligence layer: Addressed-to-me alert & Quick replies."""
        try:
            # 1. Addressed-to-me check
            alert_res = await self.llm_provider.check_addressed_to_me(
                text=text,
                user_names=self.config.friend_nicknames
            )
            if alert_res.addressed_to_user:
                await self.manager.broadcast(state.room_id, {
                    "type": "alert",
                    "kind": "name",
                    "utt_id": utt_id,
                    "vocative": alert_res.user_vocative_used,
                    "urgency": alert_res.urgency,
                    "reasoning": alert_res.reasoning,
                })

            # 2. Question check & 3 quick replies
            question_res = await self.llm_provider.detect_question_and_replies(
                text=text,
                friend_name=self.config.target_friend,
                tone_profile=self.config.friend_tone
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
