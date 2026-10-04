from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class TTSAudio(BaseModel):
    format: str # 'wav' or 'client_speech'
    sample_rate: int = 24000
    audio_base64: Optional[str] = None
    voice: str = "en-IN"


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: Optional[str] = None) -> TTSAudio:
        """Synthesize text to speech."""
        pass
