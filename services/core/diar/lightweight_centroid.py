import numpy as np
from typing import Dict, List, Optional
from scipy.signal import spectrogram
from .provider import DiarizerProvider, SpeakerSegment
from ..config import DiarizationConfig


class LightweightCentroidDiarizer(DiarizerProvider):
    """
    Online lightweight centroid speaker diarizer.
    Extracts acoustic spectral & filterbank embeddings (128-dim),
    measures cosine similarity, updates online speaker centroids,
    and supports renaming ('Speaker 1' -> 'Dadaji').
    Stores only centroid embeddings, NEVER raw audio.
    """
    def __init__(self, config: DiarizationConfig):
        self.config = config
        self.centroids: Dict[str, np.ndarray] = {}  # speaker_id -> centroid vector
        self.counts: Dict[str, int] = {}            # speaker_id -> sample count
        self.name_map: Dict[str, str] = {}          # speaker_id -> display_name
        self.next_speaker_idx = 1

    def _extract_embedding(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """Extract a 128-dimensional acoustic embedding from audio."""
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / 32768.0

        if len(audio) < sample_rate * 0.2:
            # Pad short audio
            audio = np.pad(audio, (0, int(sample_rate * 0.2) - len(audio)))

        # Compute spectrogram
        nperseg = int(sample_rate * 0.025)  # 25ms window
        noverlap = int(sample_rate * 0.010) # 10ms step
        frequencies, times, sxx = spectrogram(audio, fs=sample_rate, nperseg=nperseg, noverlap=noverlap)

        # Log power spectrum
        sxx_log = np.log1p(sxx)

        # Compress into 64 frequency bins
        n_freqs = sxx_log.shape[0]
        n_bins = 64
        bin_size = max(1, n_freqs // n_bins)
        binned = []
        for i in range(n_bins):
            start = i * bin_size
            end = min(n_freqs, (i + 1) * bin_size)
            if start < n_freqs:
                binned.append(np.mean(sxx_log[start:end, :], axis=0))
            else:
                binned.append(np.zeros(sxx_log.shape[1]))
        binned = np.array(binned) # (64, time_frames)

        # Compute mean and standard deviation across time -> 128-dim feature vector
        mean_feats = np.mean(binned, axis=1) # 64
        std_feats = np.std(binned, axis=1)   # 64
        embedding = np.concatenate([mean_feats, std_feats]) # 128

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 1e-6:
            embedding = embedding / norm
        else:
            embedding = np.zeros(128, dtype=np.float32)

        return embedding.astype(np.float32)

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(dot / (norm1 * norm2))

    def assign_speaker(self, audio: np.ndarray, sample_rate: int = 16000) -> SpeakerSegment:
        embedding = self._extract_embedding(audio, sample_rate)
        
        # If no speakers exist yet, create Speaker 1
        if not self.centroids:
            speaker_id = f"Speaker {self.next_speaker_idx}"
            self.next_speaker_idx += 1
            self.centroids[speaker_id] = embedding
            self.counts[speaker_id] = 1
            self.name_map[speaker_id] = speaker_id
            return SpeakerSegment(
                speaker_id=speaker_id,
                display_name=speaker_id,
                similarity=1.0,
                is_new_speaker=True
            )

        # Compare with existing centroids
        best_speaker = None
        best_sim = -1.0
        for s_id, centroid in self.centroids.items():
            sim = self._cosine_similarity(embedding, centroid)
            if sim > best_sim:
                best_sim = sim
                best_speaker = s_id

        # Check threshold
        if best_sim >= self.config.similarity_threshold or len(self.centroids) >= self.config.max_speakers:
            # Assign to closest existing speaker and update online centroid
            s_id = best_speaker or "Speaker 1"
            count = self.counts[s_id]
            # Exponential or running average
            alpha = 1.0 / min(count + 1, 10)
            updated = (1 - alpha) * self.centroids[s_id] + alpha * embedding
            updated_norm = np.linalg.norm(updated)
            if updated_norm > 1e-6:
                updated = updated / updated_norm
            self.centroids[s_id] = updated
            self.counts[s_id] = count + 1
            
            return SpeakerSegment(
                speaker_id=s_id,
                display_name=self.name_map.get(s_id, s_id),
                similarity=round(best_sim, 3),
                is_new_speaker=False
            )
        else:
            # Create new speaker cluster
            new_speaker_id = f"Speaker {self.next_speaker_idx}"
            self.next_speaker_idx += 1
            self.centroids[new_speaker_id] = embedding
            self.counts[new_speaker_id] = 1
            self.name_map[new_speaker_id] = new_speaker_id
            
            return SpeakerSegment(
                speaker_id=new_speaker_id,
                display_name=new_speaker_id,
                similarity=round(best_sim, 3),
                is_new_speaker=True
            )

    def rename_speaker(self, speaker_id: str, new_name: str):
        self.name_map[speaker_id] = new_name.strip()

    def get_speakers(self) -> Dict[str, str]:
        return dict(self.name_map)

    def reset(self):
        self.centroids.clear()
        self.counts.clear()
        self.name_map.clear()
        self.next_speaker_idx = 1
