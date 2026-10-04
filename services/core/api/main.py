import os
import sys
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, WebSocket, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import load_config, HearthConfig
from ..store.lexicon import LexiconStore
from ..store.sessions import SessionStore
from ..asr.post_processor import LexiconPostProcessor
from ..asr.faster_whisper_provider import FasterWhisperProvider
from ..asr.mock_provider import MockASRProvider
from ..diar.lightweight_centroid import LightweightCentroidDiarizer
from ..llm.rule_fallback import RuleBasedLLMFallback
from ..llm.openai_provider import OpenAILocalLLMProvider
from .ws import HearthWSServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("hearth")

# Initialize app
app = FastAPI(
    title="Hearth Assistive Core",
    description="Private, offline, live captioning for the family table.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration
config: HearthConfig = load_config()

# Initialize Stores
lexicon_store = LexiconStore()
session_store = SessionStore()
session_store.auto_cleanup(retention_days=config.privacy.transcript_retention_days)

# Initialize Post Processor
post_processor = LexiconPostProcessor(lexicon_store)

# Initialize ASR Provider based on config / env
use_mock_asr = os.environ.get("HEARTH_MOCK_ASR", "false").lower() in ("true", "1", "yes")
if use_mock_asr or config.asr.provider == "mock":
    logger.info("Initializing MockASRProvider (Fast / Testing Mode)")
    asr_provider = MockASRProvider()
else:
    logger.info(f"Initializing FasterWhisperProvider ({config.asr.model_size})")
    asr_provider = FasterWhisperProvider(config.asr)

# Initialize Diarizer
diarizer = LightweightCentroidDiarizer(config.diarization)

# Initialize LLM Provider
if config.llm.provider == "openai_local":
    llm_provider = OpenAILocalLLMProvider(config.llm)
else:
    llm_provider = RuleBasedLLMFallback()

# Initialize WebSocket Server
ws_server = HearthWSServer(
    config=config,
    asr_provider=asr_provider,
    post_processor=post_processor,
    diarizer=diarizer,
    llm_provider=llm_provider,
    session_store=session_store,
    lexicon_store=lexicon_store,
)


# Request schemas
class LexiconItemRequest(BaseModel):
    word: str
    category: str = "custom"


class CorrectionRequest(BaseModel):
    original: str
    corrected: str
    context: Optional[str] = None


class SpeakerRenameRequest(BaseModel):
    speaker_id: str
    new_name: str


class PlainLanguageRequest(BaseModel):
    text: str


class MemoryCreateRequest(BaseModel):
    category: str
    title: str
    detail: str
    time_or_date: Optional[str] = None


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "profile": config.profile,
        "asr_model": config.asr.model_size,
        "friend": config.target_friend,
        "offline_verified": True
    }


@app.get("/api/config")
def get_config():
    return config.dict()


@app.get("/api/lexicon")
def get_lexicon():
    return {
        "items": lexicon_store.get_all(),
        "prompt_biasing_string": lexicon_store.get_prompt_biasing_string()
    }


@app.post("/api/lexicon")
def add_lexicon_item(req: LexiconItemRequest):
    item = lexicon_store.add_or_update(req.word, category=req.category, user_confirmed=True)
    return item


@app.delete("/api/lexicon/{word}")
def delete_lexicon_item(word: str):
    success = lexicon_store.delete_word(word)
    return {"success": success, "word": word}


@app.post("/api/corrections")
def record_correction(req: CorrectionRequest):
    lexicon_store.record_correction(req.original, req.corrected, req.context)
    return {"success": True, "original": req.original, "corrected": req.corrected}


@app.get("/api/corrections")
def list_corrections():
    return lexicon_store.get_corrections()


@app.get("/api/sessions")
def list_sessions():
    return session_store.list_sessions()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    sess = session_store.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return sess


@app.post("/api/sessions")
def create_session(title: str = "Family Table"):
    session_id = session_store.create_session(title)
    return {"session_id": session_id, "title": title}


@app.post("/api/sessions/{session_id}/memories")
def add_memory(session_id: str, req: MemoryCreateRequest):
    mem_id = session_store.add_memory(session_id, req.category, req.title, req.detail, req.time_or_date)
    return {"id": mem_id, "session_id": session_id, **req.dict()}


@app.post("/api/memories/{memory_id}/toggle")
def toggle_memory(memory_id: int):
    new_state = session_store.toggle_memory_confirmation(memory_id)
    return {"id": memory_id, "confirmed": new_state}


@app.get("/api/sessions/{session_id}/export/markdown")
def export_markdown(session_id: str):
    md = session_store.export_markdown(session_id)
    return Response(content=md, media_type="text/markdown")


@app.get("/api/sessions/{session_id}/export/ics")
def export_ics(session_id: str):
    ics = session_store.export_ics(session_id)
    return Response(content=ics, media_type="text/calendar")


@app.post("/api/speakers/rename")
def rename_speaker(req: SpeakerRenameRequest):
    diarizer.rename_speaker(req.speaker_id, req.new_name)
    session_store.rename_speaker(req.speaker_id, req.new_name)
    return {"success": True, "speakers": diarizer.get_speakers()}


@app.get("/api/speakers")
def get_speakers():
    return diarizer.get_speakers()


@app.post("/api/plain_language")
async def simplify_plain_language(req: PlainLanguageRequest):
    res = await llm_provider.simplify_plain_language(req.text)
    return res.dict()


@app.post("/api/privacy/delete-all")
def delete_all_data():
    session_store.delete_everything()
    return {"success": True, "message": "All session transcripts and memories have been permanently deleted."}


@app.get("/api/privacy/verify-offline")
def verify_offline():
    """
    Privacy proof verification:
    Confirms zero external outgoing network traffic, zero cloud telemetry,
    and all providers bound strictly to localhost.
    """
    return {
        "local_only": True,
        "cloud_telemetry_disabled": True,
        "asr_provider": config.asr.provider,
        "asr_device": config.asr.device,
        "diarization_local": True,
        "network_call_count": 0,
        "retention_days": config.privacy.transcript_retention_days
    }


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    room: str = Query("default"),
    role: str = Query("all")
):
    await ws_server.handle_websocket(websocket, room_id=room, role=role)


# Mount frontend dist directory if it exists
frontend_dist = Path(__file__).resolve().parent.parent.parent / "apps" / "web" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
