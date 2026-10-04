import time
import uuid
from typing import Optional, List
import numpy as np
from .provider import ASRProvider, ASRResult, WordConfidence


class MockASRProvider(ASRProvider):
    """
    Mock ASR provider for instantaneous testing, offline container checks,
    and fast CI without requiring pre-downloaded model weights.
    """
    def __init__(self, response_text: str = "Dadaji, aapne Metformin li kya with warm water?"):
        self.response_text = response_text
        self.sample_count = 0

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000, initial_prompt: Optional[str] = None, task: str = "transcribe") -> ASRResult:
        t0 = time.time()
        self.sample_count += 1
        
        text = "Dadaji, did you take your Metformin today with warm water?" if task == "translate" else self.response_text
        words_list = text.split()
        duration = len(audio) / sample_rate if len(audio) > 0 else 1.5
        step = duration / max(len(words_list), 1)

        words: List[WordConfidence] = []
        for i, w in enumerate(words_list):
            words.append(WordConfidence(
                word=w,
                confidence=0.95 if i % 4 != 0 else 0.65, # Subtle variation for testing confidence marking
                start=round(i * step, 2),
                end=round((i + 1) * step, 2)
            ))

        latency_ms = (time.time() - t0) * 1000 + 12.0 # simulated low latency

        return ASRResult(
            utt_id=str(uuid.uuid4())[:8],
            text=text,
            language="en",
            start=0.0,
            end=round(duration, 2),
            words=words,
            is_final=True,
            latency_ms=round(latency_ms, 2)
        )

    def transcribe_stream(self, audio_chunk: np.ndarray, sample_rate: int = 16000, task: str = "transcribe") -> str:
        text = "Dadaji, did you take" if task == "translate" else self.response_text
        words = text.split()
        return " ".join(words[:min(4, len(words))])
