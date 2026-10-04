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
        self.task: str = "transcribe"  # 'transcribe' or 'translate'
        self.is_processing_partial: bool = False
        self.is_processing_final: bool = False
        self.first_capture_time: float = 0.0
        self.last_capture_time: float = 0.0


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

        elif msg_type == "set_task":
            task = data.get("task", "transcribe")
            if task in ("transcribe", "translate"):
                state.task = task
                logger.info(f"Room {state.room_id} task set to: {task}")
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "task": state.task,
                    "profile": self.config.profile,
                    "model": self.config.asr.model_size,
                    "speakers": self.diarizer.get_speakers(),
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

        # If incoming buffer has 8-byte float64 header, extract t_capture
        if len(raw_bytes) > 8:
            try:
                candidate_ts = struct.unpack("<d", raw_bytes[:8])[0]
                if 1577836800.0 < candidate_ts < 2524608000.0:  # Valid epoch timestamp (2020-2050)
                    t_capture = candidate_ts
                    audio_payload = raw_bytes[8:]
            except Exception:
                pass

        state.last_capture_time = t_capture
        state.audio_buffer.extend(audio_payload)
        
        # Audio is 16kHz 16-bit mono PCM: 2 bytes per sample -> 32000 bytes per second
        # Check energy level for VAD
        samples = np.frombuffer(audio_payload, dtype=np.int16).astype(np.float32)
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
                state.first_capture_time = t_capture
                state.current_utt_id = str(uuid.uuid4())[:8]

        # Rolling partial transcription every 800ms while speaking (non-blocking thread)
        min_bytes_for_partial = int(16000 * 2 * 0.8) # 0.8s
        if (
            state.is_speaking
            and not state.is_processing_partial
            and not state.is_processing_final
            and (now - state.last_partial_time > 0.8)
            and len(state.audio_buffer) >= min_bytes_for_partial
        ):
            state.last_partial_time = now
            state.is_processing_partial = True
            window_bytes = bytes(state.audio_buffer[-int(16000 * 2 * 2.0):])
            t_vad_endpoint = time.time()
            asyncio.create_task(self._run_async_partial(
                state, window_bytes, t_capture=t_capture, t_ws_recv=t_ws_recv, t_vad_endpoint=t_vad_endpoint
            ))

        # Check utterance end condition:
        # Either silence duration > 400ms after speaking, or maximum duration (8 seconds) reached
        silence_duration = now - state.last_speech_time
        max_duration_reached = (len(state.audio_buffer) >= 16000 * 2 * 8.0)
        
        if (state.is_speaking and silence_duration >= 0.40) or max_duration_reached:
            # Utterance complete!
            state.is_speaking = False
            state.is_processing_final = True
            total_bytes = len(state.audio_buffer)
            if total_bytes < 16000 * 2 * 0.4: # Ignore extremely brief clicks (< 400ms)
                state.audio_buffer.clear()
                state.is_processing_final = False
                return

            audio_full = np.frombuffer(state.audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            state.audio_buffer.clear()
            t_vad_endpoint = time.time()
            utt_t_capture = state.first_capture_time or t_capture

            # Execute transcription and diarization on worker thread (never blocks event loop)
            asyncio.create_task(self._run_async_final(
                state, audio_full, state.current_utt_id,
                t_capture=utt_t_capture,
                t_ws_recv=t_ws_recv,
                t_vad_endpoint=t_vad_endpoint
            ))

    async def _run_async_partial(
        self,
        state: AudioSessionState,
        window_bytes: bytes,
        t_capture: float = 0.0,
        t_ws_recv: float = 0.0,
        t_vad_endpoint: float = 0.0
    ):
        """Asynchronously compute rolling partial without blocking websocket frames."""
        try:
            t_asr_start = time.time()
            audio_f32 = np.frombuffer(window_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            partial_text = await asyncio.to_thread(self.asr_provider.transcribe_stream, audio_f32, task=state.task)
            t_asr_end = time.time()
            t_send = time.time()

            if partial_text and state.is_speaking:
                t_cap = t_capture or t_ws_recv or t_asr_start
                await self.manager.broadcast(state.room_id, {
                    "type": "partial",
                    "utt_id": state.current_utt_id,
                    "text": partial_text,
                    "lang": "en",
                    "task": state.task,
                    "t_capture": round(t_cap, 4),
                    "t_ws_recv": round(t_ws_recv, 4),
                    "t_vad_endpoint": round(t_vad_endpoint, 4),
                    "t_asr_start": round(t_asr_start, 4),
                    "t_asr_end": round(t_asr_end, 4),
                    "t_send": round(t_send, 4),
                    "latency_breakdown": {
                        "ws_transit_ms": round((t_ws_recv - t_cap) * 1000, 1) if t_ws_recv >= t_cap else 0.0,
                        "vad_ms": round((t_vad_endpoint - t_ws_recv) * 1000, 1) if t_vad_endpoint >= t_ws_recv else 0.0,
                        "asr_ms": round((t_asr_end - t_asr_start) * 1000, 1),
                        "total_latency_ms": round((t_send - t_cap) * 1000, 1),
                    }
                })
        except Exception as e:
            logger.debug(f"Partial transcribe error: {e}")
        finally:
            state.is_processing_partial = False

    async def _run_async_final(
        self,
        state: AudioSessionState,
        audio_full: np.ndarray,
        utt_id: str,
        t_capture: float = 0.0,
        t_ws_recv: float = 0.0,
        t_vad_endpoint: float = 0.0
    ):
        """Asynchronously compute final caption and diarization on worker threads."""
        try:
            t_asr_start = time.time()
            prompt = await asyncio.to_thread(self.lexicon_store.get_prompt_biasing_string)
            result: ASRResult = await asyncio.to_thread(
                self.asr_provider.transcribe, audio_full, initial_prompt=prompt, task=state.task
            )
            t_asr_end = time.time()

            t_diar_start = time.time()
            speaker_seg = await asyncio.to_thread(self.diarizer.assign_speaker, audio_full)
            t_diar_end = time.time()

            t_post_start = time.time()
            result = await asyncio.to_thread(self.post_processor.process_result, result)
            t_post_end = time.time()

            # Skip empty hallucinations
            if not result.text.strip():
                return

            t_send = time.time()
            t_cap = t_capture or t_ws_recv or t_asr_start
            total_latency = (t_send - t_cap) * 1000

            # Broadcast final caption IMMEDIATELY (critical path sub-2s)
            final_msg = {
                "type": "final",
                "utt_id": utt_id,
                "speaker": speaker_seg.display_name,
                "speaker_id": speaker_seg.speaker_id,
                "text": result.text,
                "lang": result.language,
                "task": state.task,
                "start": result.start,
                "end": result.end,
                "words": [{"w": w.word, "conf": w.confidence} for w in result.words],
                "latency_ms": round(total_latency, 1),
                "t_capture": round(t_cap, 4),
                "t_ws_recv": round(t_ws_recv, 4),
                "t_vad_endpoint": round(t_vad_endpoint, 4),
                "t_asr_start": round(t_asr_start, 4),
                "t_asr_end": round(t_asr_end, 4),
                "t_diar_end": round(t_diar_end, 4),
                "t_post_end": round(t_post_end, 4),
                "t_send": round(t_send, 4),
                "latency_breakdown": {
                    "ws_transit_ms": round((t_ws_recv - t_cap) * 1000, 1) if t_ws_recv >= t_cap else 0.0,
                    "vad_endpoint_ms": round((t_vad_endpoint - t_ws_recv) * 1000, 1) if t_vad_endpoint >= t_ws_recv else 0.0,
                    "asr_ms": round((t_asr_end - t_asr_start) * 1000, 1),
                    "diar_ms": round((t_diar_end - t_diar_start) * 1000, 1),
                    "post_ms": round((t_post_end - t_post_start) * 1000, 1),
                    "total_spoken_to_send_ms": round(total_latency, 1),
                }
            }
            await self.manager.broadcast(state.room_id, final_msg)

            # Append to session history & SQLite
            now = time.time()
            utt_record = {
                "speaker": speaker_seg.display_name,
                "text": result.text,
                "utt_id": utt_id,
                "lang": result.language,
                "time": now,
            }
            state.recent_utterance_history.append(utt_record)
            if len(state.recent_utterance_history) > 30:
                state.recent_utterance_history.pop(0)

            await asyncio.to_thread(
                self.session_store.append_utterance,
                session_id=state.session_id,
                utt_id=utt_id,
                speaker=speaker_seg.display_name,
                text=result.text,
                lang=result.language,
                start_sec=result.start,
                end_sec=result.end,
                confidence=float(np.mean([w.confidence for w in result.words])) if result.words else 0.9,
            )

            # Fire async intelligence checks concurrently (never blocks ASR)
            asyncio.create_task(self._run_async_intelligence(state, utt_id, result.text))
        except Exception as e:
            logger.error(f"Error in async final processing: {e}", exc_info=True)
        finally:
            state.is_processing_final = False

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
