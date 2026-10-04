from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
import numpy as np
from pydantic import BaseModel


class SpeakerSegment(BaseModel):
    speaker_id: str
    display_name: str
    similarity: float
    is_new_speaker: bool = False


class DiarizerProvider(ABC):
    @abstractmethod
    def assign_speaker(self, audio: np.ndarray, sample_rate: int = 16000) -> SpeakerSegment:
        """Assign speaker label to audio segment via online clustering."""
        pass

    @abstractmethod
    def rename_speaker(self, speaker_id: str, new_name: str):
        """Map speaker cluster ID to user-defined name."""
        pass

    @abstractmethod
    def get_speakers(self) -> Dict[str, str]:
        """Return dict of speaker_id -> display_name."""
        pass

    @abstractmethod
    def reset(self):
        """Reset clusters for a new session."""
        pass
