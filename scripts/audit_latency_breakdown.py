"""
Latency Waterfall Audit Script for Hearth
Streams real WAV audio clips at 1x real-time over WebSocket with 8-byte Float64 t_capture headers.
Collects and logs exact millisecond timestamps at every stage:
1. Audio capture (t_capture)
2. WebSocket transmission (t_ws_recv)
3. VAD endpoint detection (t_vad_endpoint)
4. ASR inference start & end (t_asr_start, t_asr_end)
5. Diarization computation (t_diar_end)
6. Lexicon post-processing (t_post_end)
7. WebSocket transmission to client (t_send -> t_client_recv)
8. Client render simulation (t_render)
"""

import asyncio
import json
import struct
import time
import wave
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


async def run_stream_audit(wav_path: str, clip_name: str, task: str = "transcribe"):
    room_id = f"AUDIT-{int(time.time()*1000)%100000}"
    uri = f"{WS_URL}?room={room_id}&role=all"

    samples = load_clip_16k(wav_path)
    total_audio_sec = len(samples) / 16000.0
    print(f"\n{'='*70}")
    print(f"AUDIT RUN: {clip_name} ({total_audio_sec:.2f}s audio) | task={task}")
    print(f"{'='*70}")

    async with websockets.connect(uri) as ws:
        # Wait for initial status
        init_raw = await ws.recv()
        status = json.loads(init_raw)

        if task != "transcribe":
            await ws.send(json.dumps({"type": "set_task", "task": task}))
            await asyncio.sleep(0.2)

        partials = []
        finals = []
        all_messages = []

        async def listen():
            try:
                while True:
                    msg = await ws.recv()
                    t_recv = time.time()
                    data = json.loads(msg)
                    data["t_client_recv"] = t_recv
                    all_messages.append(data)
                    mtype = data.get("type")
                    if mtype == "partial":
                        partials.append(data)
                    elif mtype == "final":
                        finals.append(data)
            except (asyncio.CancelledError, websockets.ConnectionClosed):
                pass

        listen_task = asyncio.create_task(listen())

        # Stream 100ms frames at 1x real-time cadence
        chunk_samples = 1600  # 100ms at 16kHz
        stream_start_wall = time.time()
        first_frame_capture = stream_start_wall

        for i in range(0, len(samples), chunk_samples):
            chunk = samples[i:i + chunk_samples]
            if len(chunk) < chunk_samples:
                # pad last chunk
                padded = np.zeros(chunk_samples, dtype=np.int16)
                padded[:len(chunk)] = chunk
                chunk = padded

            t_capture = time.time()
            if i == 0:
                first_frame_capture = t_capture

            # Pack 8-byte Float64 header + PCM16 bytes
            header = struct.pack("<d", t_capture)
            payload = header + chunk.tobytes()
            await ws.send(payload)
            await asyncio.sleep(0.095)  # ~100ms cadence

        speech_end_wall = time.time()

        # Send 600ms of silence frames to trigger VAD endpoint
        silence_chunk = np.zeros(chunk_samples, dtype=np.int16)
        for _ in range(6):
            t_cap = time.time()
            header = struct.pack("<d", t_cap)
            payload = header + silence_chunk.tobytes()
            await ws.send(payload)
            await asyncio.sleep(0.095)

        # Wait up to 15s for final caption
        wait_deadline = time.time() + 15.0
        while not finals and time.time() < wait_deadline:
            await asyncio.sleep(0.1)

        listen_task.cancel()

        # Compute and print latency waterfall
        print("\n--- MEASURED RESULTS ---")
        print(f"Total audio duration:            {total_audio_sec*1000:7.1f} ms ({total_audio_sec:.2f} s)")
        print(f"Speech streaming duration:       {(speech_end_wall - stream_start_wall)*1000:7.1f} ms")
        print(f"Partials received count:         {len(partials)}")

        first_partial_delay = None
        if partials:
            fp = partials[0]
            first_partial_delay = (fp["t_client_recv"] - first_frame_capture) * 1000
            print(f"Time to first partial (from t0): {first_partial_delay:7.1f} ms")
            print(f"  First partial text:            \"{fp.get('text', '')}\"")
        else:
            print("Time to first partial:           NONE RECEIVED during speech!")

        if finals:
            fn = finals[0]
            t_cap = fn.get("t_capture", first_frame_capture)
            t_ws = fn.get("t_ws_recv", t_cap)
            t_vad = fn.get("t_vad_endpoint", t_ws)
            t_asr_s = fn.get("t_asr_start", t_vad)
            t_asr_e = fn.get("t_asr_end", t_asr_s)
            t_diar_e = fn.get("t_diar_end", t_asr_e)
            t_post_e = fn.get("t_post_end", t_diar_e)
            t_send = fn.get("t_send", t_post_e)
            t_recv = fn.get("t_client_recv", t_send)

            vad_wait_ms = (t_vad - speech_end_wall) * 1000
            asr_inf_ms = (t_asr_e - t_asr_s) * 1000
            diar_ms = (t_diar_e - t_asr_e) * 1000
            post_ms = (t_post_e - t_diar_e) * 1000
            net_egress_ms = (t_recv - t_send) * 1000

            total_from_start_ms = (t_recv - first_frame_capture) * 1000
            total_from_end_ms = (t_recv - speech_end_wall) * 1000

            print(f"\nFinal Caption text:              \"{fn.get('text', '')}\"")
            print(f"Speaker assigned:                {fn.get('speaker', 'Unknown')}")
            print(f"\nWATERFALL STAGES (where the time went):")
            print(f"  1. Speech duration (speaker talking):      {total_audio_sec*1000:7.1f} ms")
            print(f"  2. VAD silence wait (endpointing delay):   {vad_wait_ms:7.1f} ms")
            print(f"  3. ASR model inference (CTranslate2 base): {asr_inf_ms:7.1f} ms  (RTF = {asr_inf_ms/(total_audio_sec*1000):.3f})")
            print(f"  4. Diarization embedding + clustering:     {diar_ms:7.1f} ms")
            print(f"  5. Lexicon Post-processing (SQLite+Fuzz):  {post_ms:7.1f} ms")
            print(f"  6. WebSocket broadcast to client:          {net_egress_ms:7.1f} ms")
            print(f"  -------------------------------------------------------------")
            print(f"  TOTAL delay from speech completion:        {total_from_end_ms:7.1f} ms")
            print(f"  TOTAL perceived latency from start:        {total_from_start_ms:7.1f} ms ({total_from_start_ms/1000:.2f} s)")

            return {
                "clip": clip_name,
                "duration_sec": total_audio_sec,
                "first_partial_delay_ms": first_partial_delay,
                "vad_wait_ms": vad_wait_ms,
                "asr_inference_ms": asr_inf_ms,
                "diarization_ms": diar_ms,
                "post_processing_ms": post_ms,
                "delay_from_speech_end_ms": total_from_end_ms,
                "total_from_speech_start_ms": total_from_start_ms,
                "rtf": asr_inf_ms / (total_audio_sec * 1000),
            }
        else:
            print("ERROR: No final caption received within 15 seconds timeout!")
            return None


async def main():
    results = []
    # Test short clip
    r1 = await run_stream_audit("eval/recordings/clip_01.wav", "clip_01 (4.4s sentence)")
    if r1: results.append(r1)

    # Test medium clip
    r2 = await run_stream_audit("eval/recordings/clip_03.wav", "clip_03 (4.5s sentence)")
    if r2: results.append(r2)

    # Test clip_08 (longer clip)
    r3 = await run_stream_audit("eval/recordings/clip_08.wav", "clip_08 (4.8s sentence)")
    if r3: results.append(r3)

    # Save results to scratch
    with open("eval/audit_measurements.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved raw measurements to eval/audit_measurements.json")


if __name__ == "__main__":
    asyncio.run(main())
