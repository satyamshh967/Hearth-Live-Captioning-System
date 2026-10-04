from typing import Optional
from .provider import TTSProvider, TTSAudio
from ..config import TTSConfig


class WebSpeechTTSProvider(TTSProvider):
    """
    Directs the client browser to use its local Web Speech API synthesis.
    This saves CPU on small hosts, provides native localized speech on phones/tablets,
    and runs completely offline without downloading multi-gigabyte TTS models.
    """
    def __init__(self, config: TTSConfig):
        self.config = config

    def synthesize(self, text: str, voice: Optional[str] = None) -> TTSAudio:
        return TTSAudio(
            format="client_speech",
            voice=voice or self.config.voice,
            audio_base64=None
        )
