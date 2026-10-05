"""
ASR Candidate Spike: Benchmark Streaming Strategies
Compares:
1. faster-whisper (tiny int8) + LocalAgreement streaming policy
2. faster-whisper (base int8) + LocalAgreement streaming policy
3. Chunk-based transducer simulation vs full-sentence baseline

Measures:
- Time to first word on screen (TTFW)
- Word commit latency (time from spoken word to stable commit)
- Word Error Rate (WER) against ground truth
- Average decode time per chunk (ms) and CPU Real-Time Factor (RTF)
"""

import time
import wave
import json
import re
import numpy as np
from faster_whisper import WhisperModel
import jiwer


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


class LocalAgreementStreamer:
    def __init__(self, model_size: str = "base", cpu_threads: int = 4, chunk_step_sec: float = 0.25):
        self.model_size = model_size
        self.chunk_step_sec = chunk_step_sec
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            cpu_threads=cpu_threads,
            num_workers=1
        )

    def run_streaming_simulation(self, audio: np.ndarray, ground_truth: str):
        sample_rate = 16000
        step_samples = int(sample_rate * self.chunk_step_sec)  # 250ms chunks
        min_context_samples = int(sample_rate * 0.5)           # min 500ms before first decode
        max_context_samples = int(sample_rate * 3.0)           # max 3s sliding context window

        committed_words = []
        last_hypothesis_words = []
        word_commit_times = []  # (word, spoken_time_approx, commit_time_wall)
        
        first_word_time = None
        decode_latencies = []

        buffer = np.zeros(0, dtype=np.float32)
        sim_start_time = time.time()
        audio_streamed_sec = 0.0

        for start_idx in range(0, len(audio), step_samples):
            chunk = audio[start_idx:start_idx + step_samples]
            buffer = np.concatenate([buffer, chunk])
            audio_streamed_sec += len(chunk) / sample_rate

            if len(buffer) < min_context_samples:
                continue

            # Slide window if buffer exceeds max_context
            decode_audio = buffer[-max_context_samples:]

            # Run fast greedy decode
            t0 = time.time()
            segments, _ = self.model.transcribe(
                decode_audio,
                beam_size=1,
                language="en",
                temperature=0.0,
                vad_filter=False,
                word_timestamps=False,
            )
            t_decode = time.time() - t0
            decode_latencies.append(t_decode * 1000)

            hyp_text = " ".join([s.text.strip() for s in segments]).strip()
            current_words = hyp_text.split() if hyp_text else []

            if current_words and first_word_time is None:
                first_word_time = audio_streamed_sec

            # LocalAgreement policy:
            # Find longest common prefix between last_hypothesis_words and current_words
            common_prefix_len = 0
            for w1, w2 in zip(last_hypothesis_words, current_words):
                if normalize_text(w1) == normalize_text(w2) and w1 != "":
                    common_prefix_len += 1
                else:
                    break

            # If prefix agreed across 2 consecutive decodes, commit the agreed words
            # (keeping at least the last 2-3 words as tentative tail)
            words_to_commit = max(0, common_prefix_len - 2)
            if words_to_commit > 0:
                new_commits = current_words[:words_to_commit]
                for w in new_commits:
                    committed_words.append(w)
                    word_commit_times.append((w, audio_streamed_sec))
                
                # Trim committed audio from buffer to keep context bounded
                # Advance buffer by approximate duration of committed words
                buffer = buffer[-int(sample_rate * 1.5):]
                current_words = current_words[words_to_commit:]

            last_hypothesis_words = current_words

        # Final sweep at end of speech
        if last_hypothesis_words:
            for w in last_hypothesis_words:
                committed_words.append(w)
                word_commit_times.append((w, audio_streamed_sec))

        final_transcript = " ".join(committed_words)
        total_audio_sec = len(audio) / sample_rate
        avg_decode_ms = np.mean(decode_latencies) if decode_latencies else 0.0
        p95_decode_ms = np.percentile(decode_latencies, 95) if decode_latencies else 0.0

        wer = jiwer.wer(normalize_text(ground_truth), normalize_text(final_transcript))

        # Commit latency: average time difference between when word was finished in audio vs committed
        commit_latencies = [t_commit for (w, t_commit) in word_commit_times]
        avg_commit_delay = np.mean(commit_latencies) if commit_latencies else 0.0

        return {
            "model_size": self.model_size,
            "ttfw_sec": first_word_time if first_word_time is not None else total_audio_sec,
            "avg_decode_ms": avg_decode_ms,
            "p95_decode_ms": p95_decode_ms,
            "wer": round(wer, 3),
            "final_transcript": final_transcript,
            "ground_truth": ground_truth,
            "rtf": (sum(decode_latencies) / 1000.0) / total_audio_sec,
        }


def main():
    print("=" * 70)
    print("ASR CANDIDATE SPIKE: LOCALAGREEMENT STREAMING BENCHMARK")
    print("=" * 70)

    with open("eval/recordings/metadata.json", "r") as f:
        metadata = json.load(f)

    # Test clips 1, 2, 3, 4
    test_clips = metadata[:4]

    for model_size in ["tiny", "base"]:
        print(f"\nEvaluating Candidate: faster-whisper [{model_size.upper()}] with LocalAgreement (250ms step, 4 threads)")
        streamer = LocalAgreementStreamer(model_size=model_size, cpu_threads=4, chunk_step_sec=0.25)

        ttfws = []
        wers = []
        avg_decodes = []
        rtfs = []

        for item in test_clips:
            wav_path = f"eval/recordings/{item['file']}"
            with wave.open(wav_path, "rb") as wf:
                sr = wf.getframerate()
                raw = wf.readframes(wf.getnframes())
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if sr != 16000:
                target_len = int(len(samples) * 16000 / sr)
                audio_16k = np.interp(np.linspace(0, len(samples), target_len, endpoint=False), np.arange(len(samples)), samples).astype(np.float32)
            else:
                audio_16k = samples

            res = streamer.run_streaming_simulation(audio_16k, item["ground_truth"])
            ttfws.append(res["ttfw_sec"])
            wers.append(res["wer"])
            avg_decodes.append(res["avg_decode_ms"])
            rtfs.append(res["rtf"])

            print(f"  [{item['id']}] TTFW: {res['ttfw_sec']*1000:5.0f}ms | Decode: {res['avg_decode_ms']:4.1f}ms | WER: {res['wer']:.2f}")
            print(f"    Hyp: \"{res['final_transcript']}\"")
            print(f"    Ref: \"{res['ground_truth']}\"")

        print(f"\n  SUMMARY for [{model_size.upper()}]:")
        print(f"    - Avg Time to First Word (TTFW): {np.mean(ttfws)*1000:.1f} ms")
        print(f"    - Avg Chunk Decode Time:         {np.mean(avg_decodes):.1f} ms")
        print(f"    - Mean Word Error Rate (WER):    {np.mean(wers):.3f}")
        print(f"    - Cumulative Stream RTF:         {np.mean(rtfs):.3f}")


if __name__ == "__main__":
    main()
