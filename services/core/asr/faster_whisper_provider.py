import time
import uuid
import logging
from typing import Optional, List
import numpy as np
try:
    from faster_whisper import WhisperModel
except Exception as _fw_err:
    WhisperModel = None

from .provider import ASRProvider, ASRResult, WordConfidence
from ..config import ASRConfig

logger = logging.getLogger(__name__)


class FasterWhisperProvider(ASRProvider):
    def __init__(self, config: ASRConfig):
        self.config = config
        if WhisperModel is None:
            raise RuntimeError("faster_whisper is not available in this environment (e.g. DLL/AV policy blocked).")
        logger.info(f"Initializing FasterWhisperProvider: model={config.model_size}, device={config.device}, compute={config.compute_type}")
        
        device = config.device
        compute_type = config.compute_type
        if device == "auto":
            # auto-detect
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                if device == "cpu" and compute_type == "float16":
                    compute_type = "int8"
            except Exception:
                device = "cpu"
                compute_type = "int8"
                
        self.model = WhisperModel(
            config.model_size,
            device=device,
            compute_type=compute_type,
            download_root=None,
        )

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000, initial_prompt: Optional[str] = None, task: str = "transcribe") -> ASRResult:
        t0 = time.time()
        
        # Audio should be float32 normalized between -1.0 and 1.0
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / 32768.0

        prompt = initial_prompt or self.config.initial_prompt
        vad_parameters = {
            "min_silence_duration_ms": self.config.min_silence_duration_ms,
        } if self.config.vad_filter else None

        segments, info = self.model.transcribe(
            audio,
            beam_size=self.config.beam_size,
            language=self.config.language,  # None means auto-detect
            task=task,
            initial_prompt=prompt,
            vad_filter=self.config.vad_filter,
            vad_parameters=vad_parameters,
            word_timestamps=True,
        )

        all_text = []
        all_words: List[WordConfidence] = []
        start_time = 0.0
        end_time = len(audio) / sample_rate

        for seg in segments:
            all_text.append(seg.text.strip())
            if seg.words:
                for w in seg.words:
                    all_words.append(WordConfidence(
                        word=w.word.strip(),
                        confidence=round(float(w.probability), 3),
                        start=round(float(w.start), 2),
                        end=round(float(w.end), 2),
                    ))

        full_text = " ".join(all_text).strip()
        latency_ms = (time.time() - t0) * 1000

        return ASRResult(
            utt_id=str(uuid.uuid4())[:8],
            text=full_text,
            language=info.language if hasattr(info, "language") else "en",
            start=round(start_time, 2),
            end=round(end_time, 2),
            words=all_words,
            is_final=True,
            latency_ms=round(latency_ms, 2)
        )

    def transcribe_stream(self, audio_chunk: np.ndarray, sample_rate: int = 16000, task: str = "transcribe") -> str:
        """Fast partial transcription or translation for rolling stream (beam_size=1, no word timestamps)."""
        if len(audio_chunk) < sample_rate * 0.5:
            return ""
            
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)
        if np.max(np.abs(audio_chunk)) > 1.0:
            audio_chunk = audio_chunk / 32768.0

        segments, _ = self.model.transcribe(
            audio_chunk,
            beam_size=1,
            language=self.config.language,
            task=task,
            initial_prompt=self.config.initial_prompt,
            vad_filter=False,
            word_timestamps=False,
        )
        texts = [s.text.strip() for s in segments]
        return " ".join(texts).strip()
