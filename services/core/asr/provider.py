from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from pydantic import BaseModel


class WordConfidence(BaseModel):
    word: str
    confidence: float
    start: float
    end: float


class ASRResult(BaseModel):
    utt_id: str
    text: str
    language: str
    start: float
    end: float
    words: List[WordConfidence]
    is_final: bool = True
    latency_ms: float = 0.0


class ASRProvider(ABC):
    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000, initial_prompt: Optional[str] = None) -> ASRResult:
        """Transcribe an audio segment (16kHz float32 mono)."""
        pass

    @abstractmethod
    def transcribe_stream(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> str:
        """Lightweight partial transcription for rolling stream display."""
        pass
