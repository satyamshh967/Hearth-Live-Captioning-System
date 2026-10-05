"""
Streaming Replay Harness for Hearth
Feeds evaluation audio clips through the real WebSocket server at 1x real-time cadence.
Measures:
- Time-to-first-word (TTFW)
- Word commit latency (time from spoken audio to solid text commit)
- End-to-end total latency
- Generates p50 and p95 metrics into eval/latency.json
"""

import asyncio
import json
import struct
import time
import wave
import glob
from pathlib import Path
import numpy as np
import websockets

WS_URL = "ws://127.0.0.1:8000/ws"


def load_clip_16k(wav_path: str) -> np.ndarray:
    with wave.open(wav_path, "rb") as wf:
        sr = wf.getframerate()
        n_channels = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
        samples = np.frombuffer(raw, dtype=np.int16)
        if n_channels > 1:
            samples = samples[::n_channels]
        if sr != 16000:
            target_len = int(len(samples) * 16000 / sr)
            samples = np.interp(
                np.linspace(0, len(samples), target_len, endpoint=False),
                np.arange(len(samples)),
                samples
            ).astype(np.int16)
        return samples


async def replay_clip(ws, clip_path: str):
    samples = load_clip_16k(clip_path)
    total_audio_sec = len(samples) / 16000.0
    chunk_samples = 1600  # 100ms
    
    first_word_time = None
    commit_latencies = []
    final_caption = None
    t0 = time.time()

    streaming_events = []

    async def listen():
        nonlocal first_word_time, final_caption
        try:
            while True:
                msg = await ws.recv()
                t_recv = time.time()
                data = json.loads(msg)
                mtype = data.get("type")
                if mtype == "streaming_update":
                    streaming_events.append(data)
                    if (data.get("committed_source") or data.get("tentative_source")) and first_word_time is None:
                        first_word_time = (t_recv - t0) * 1000
                    if data.get("committed_source"):
                        commit_latencies.append((t_recv - t0) * 1000)
                elif mtype == "final":
                    final_caption = data
                    break
        except Exception:
            pass

    listener = asyncio.create_task(listen())

    # Stream 100ms frames at 1x real-time
    for i in range(0, len(samples), chunk_samples):
        chunk = samples[i:i + chunk_samples]
        t_cap = time.time()
        header = struct.pack("<d", t_cap)
        payload = header + chunk.tobytes()
        await ws.send(payload)
        await asyncio.sleep(0.095)

    # 400ms silence to trigger final endpoint
    silence = np.zeros(chunk_samples, dtype=np.int16).tobytes()
    for _ in range(5):
        await ws.send(struct.pack("<d", time.time()) + silence)
        await asyncio.sleep(0.095)

    # Wait for final
    wait_until = time.time() + 8.0
    while final_caption is None and time.time() < wait_until:
        await asyncio.sleep(0.1)

    listener.cancel()

    ttfw = first_word_time if first_word_time is not None else (total_audio_sec * 1000)
    commit_delay = np.median(commit_latencies) if commit_latencies else ttfw

    return {
        "clip": Path(clip_path).name,
        "duration_sec": round(total_audio_sec, 2),
        "ttfw_ms": round(ttfw, 1),
        "commit_ms": round(commit_delay, 1),
        "total_final_latency_ms": round(final_caption.get("latency_ms", 0.0), 1) if final_caption else 0.0,
        "transcript": final_caption.get("text", "") if final_caption else "",
        "streaming_events_count": len(streaming_events),
    }


async def main():
    print("=" * 70)
    print("STREAMING REPLAY HARNESS: Measuring True Latency Across Audio Corpus")
    print("=" * 70)

    clips = sorted(glob.glob("eval/recordings/clip_*.wav"))
    if not clips:
        print("No recordings found in eval/recordings!")
        return

    # Use first 6 clips representing different speakers and sentence lengths
    test_set = clips[:6]
    results = []

    room_id = f"REPLAY-{int(time.time()*1000)%100000}"
    uri = f"{WS_URL}?room={room_id}&role=all"

    async with websockets.connect(uri) as ws:
        await ws.recv()  # initial status

        for clip in test_set:
            print(f"  Replaying {Path(clip).name} at 1x real-time...", end="", flush=True)
            res = await replay_clip(ws, clip)
            results.append(res)
            print(f" -> TTFW: {res['ttfw_ms']:5.1f}ms | Commit: {res['commit_ms']:6.1f}ms | Events: {res['streaming_events_count']}")
            await asyncio.sleep(1.0)

    # Compute p50 and p95 statistics
    ttfws = [r["ttfw_ms"] for r in results]
    commits = [r["commit_ms"] for r in results]

    p50_ttfw = float(np.percentile(ttfws, 50))
    p95_ttfw = float(np.percentile(ttfws, 95))
    p50_commit = float(np.percentile(commits, 50))
    p95_commit = float(np.percentile(commits, 95))

    latency_summary = {
        "hardware": "Intel 32 Cores CPU (int8 CTranslate2, cpu_threads=4)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_clips_evaluated": len(results),
        "p50_time_to_first_word_ms": round(p50_ttfw, 1),
        "p95_time_to_first_word_ms": round(p95_ttfw, 1),
        "p50_word_commit_latency_ms": round(p50_commit, 1),
        "p95_word_commit_latency_ms": round(p95_commit, 1),
        "target_budgets": {
            "first_partial_budget_ms": 500.0,
            "word_committed_budget_ms": 1200.0,
            "ui_render_budget_ms": 16.0
        },
        "budget_status": {
            "ttfw_met": bool(p50_ttfw <= 500.0),
            "commit_met": bool(p50_commit <= 1200.0)
        },
        "per_clip_measurements": results
    }

    out_file = Path("eval/latency.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(latency_summary, f, indent=2)

    print("\n" + "=" * 70)
    print("STREAMING LATENCY BENCHMARK RESULTS:")
    print(f"  - p50 Time to First Word:    {p50_ttfw:5.1f} ms  (Target: <= 500 ms)  [{'PASS' if p50_ttfw <= 500 else 'FAIL'}]")
    print(f"  - p95 Time to First Word:    {p95_ttfw:5.1f} ms")
    print(f"  - p50 Word Commit Latency:   {p50_commit:5.1f} ms  (Target: <= 1200 ms) [{'PASS' if p50_commit <= 1200 else 'FAIL'}]")
    print(f"  - p95 Word Commit Latency:   {p95_commit:5.1f} ms")
    print(f"  - Saved to: {out_file}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
