import os
from pathlib import Path
from typing import Optional, List
import yaml
from pydantic import BaseModel, Field


class ASRConfig(BaseModel):
    provider: str = "faster_whisper"
    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 2
    language: Optional[str] = None  # None = auto-detect per utterance for code-switching
    initial_prompt: str = ""
    vad_filter: bool = True
    min_silence_duration_ms: int = 300
    chunk_duration_sec: float = 2.0


class DiarizationConfig(BaseModel):
    provider: str = "lightweight_centroid"
    min_speakers: int = 1
    max_speakers: int = 6
    similarity_threshold: float = 0.68
    embedding_dimension: int = 128


class LLMConfig(BaseModel):
    provider: str = "local_rule_fallback"
    endpoint: str = "http://localhost:11434/v1"
    model: str = "qwen2.5:3b"
    timeout_sec: float = 3.0
    temperature: float = 0.1


class TTSConfig(BaseModel):
    provider: str = "web_speech_fallback"
    voice: str = "en-IN"


class PrivacyConfig(BaseModel):
    store_audio: bool = False
    transcript_retention_days: int = 7
    allow_network_telemetry: bool = False


class HearthConfig(BaseModel):
    profile: str = "balanced"
    target_friend: str = "Ramesh (Dadaji)"
    friend_nicknames: List[str] = Field(default_factory=lambda: ["dadaji", "dada", "ramesh", "rameshji", "uncle"])
    friend_tone: str = "warm, polite, grandfatherly, concise Hinglish"
    asr: ASRConfig = Field(default_factory=ASRConfig)
    diarization: DiarizationConfig = Field(default_factory=DiarizationConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


def load_config(profile_name: Optional[str] = None) -> HearthConfig:
    """Load configuration from YAML file or environment."""
    profile = profile_name or os.environ.get("HEARTH_PROFILE", "balanced")
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_file = base_dir / "configs" / f"{profile}.yaml"

    data = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    config = HearthConfig(**data)
    config.profile = profile
    return config
