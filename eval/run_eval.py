import os
import sys
import json
import time
import asyncio
from pathlib import Path
import numpy as np
import soundfile as sf
import jiwer

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.core.config import load_config, HearthConfig
from services.core.store.lexicon import LexiconStore
from services.core.asr.post_processor import LexiconPostProcessor
from services.core.asr.faster_whisper_provider import FasterWhisperProvider
from services.core.asr.mock_provider import MockASRProvider
from services.core.llm.rule_fallback import RuleBasedLLMFallback


def compute_metrics(tp: int, fp: int, fn: int, tn: int):
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "accuracy": round(accuracy, 3),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn
    }


async def evaluate_intent_dataset(dataset_path: Path):
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    llm = RuleBasedLLMFallback()
    user_names = ["Dadaji", "Dada", "Ramesh", "Rameshji", "Uncle"]

    addr_tp = addr_fp = addr_fn = addr_tn = 0
    q_tp = q_fp = q_fn = q_tn = 0

    print(f"\n--- Evaluating Intent Layer on {len(data)} Hand-Labeled Utterances ---")

    for item in data:
        text = item["text"]
        gt_addr = item["addressed_to_me"]
        gt_q = item["is_question"]

        # Run Addressed-to-me check
        alert_res = await llm.check_addressed_to_me(text, user_names)
        pred_addr = alert_res.addressed_to_user

        if pred_addr and gt_addr:
            addr_tp += 1
        elif pred_addr and not gt_addr:
            addr_fp += 1
        elif not pred_addr and gt_addr:
            addr_fn += 1
        else:
            addr_tn += 1

        # Run Question check
        q_res = await llm.detect_question_and_replies(text, "Dadaji", "warm")
        pred_q = q_res.is_question

        if pred_q and gt_q:
            q_tp += 1
        elif pred_q and not gt_q:
            q_fp += 1
        elif not pred_q and gt_q:
            q_fn += 1
        else:
            q_tn += 1

    addr_metrics = compute_metrics(addr_tp, addr_fp, addr_fn, addr_tn)
    q_metrics = compute_metrics(q_tp, q_fp, q_fn, q_tn)

    print(f"Addressed-to-Me: Precision={addr_metrics['precision']:.3f}, Recall={addr_metrics['recall']:.3f}, F1={addr_metrics['f1']:.3f} (Acc={addr_metrics['accuracy']:.3f})")
    print(f"Question Detect: Precision={q_metrics['precision']:.3f}, Recall={q_metrics['recall']:.3f}, F1={q_metrics['f1']:.3f} (Acc={q_metrics['accuracy']:.3f})")

    return {
        "addressed_to_me": addr_metrics,
        "question_detection": q_metrics,
        "sample_size": len(data)
    }


def evaluate_asr_clips(recordings_dir: Path, config: HearthConfig):
    meta_path = recordings_dir / "metadata.json"
    if not meta_path.exists():
        print(f"Metadata file not found at {meta_path}. Run generate_evaluation_dataset.py first.")
        return {}

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Initialize ASR and post-processor
    lex_store = LexiconStore()
    post_processor = LexiconPostProcessor(lex_store)

    use_mock = os.environ.get("HEARTH_MOCK_ASR", "false").lower() in ("true", "1", "yes")
    if use_mock:
        asr = MockASRProvider()
    else:
        asr = FasterWhisperProvider(config.asr)

    latencies = []
    ground_truths = []
    raw_hypotheses = []
    lexicon_hypotheses = []

    print(f"\n--- Transcribing {len(metadata)} Clips with Faster-Whisper ({config.asr.model_size}) ---")

    for item in metadata:
        wav_path = recordings_dir / item["file"]
        audio, sr = sf.read(str(wav_path))
        if audio.ndim > 1:
            audio = audio[:, 0]

        t0 = time.time()
        # Raw transcription without initial_prompt
        res_raw = asr.transcribe(audio, sample_rate=sr, initial_prompt="")
        
        # Biased transcription with initial prompt + post processor
        prompt = lex_store.get_prompt_biasing_string()
        res_biased = asr.transcribe(audio, sample_rate=sr, initial_prompt=prompt)
        res_corrected = post_processor.process_result(res_biased)
        
        latency = (time.time() - t0) * 1000
        latencies.append(latency)

        gt = item["ground_truth"]
        ground_truths.append(gt)
        raw_hypotheses.append(res_raw.text)
        lexicon_hypotheses.append(res_corrected.text)

        raw_safe = res_raw.text.encode('ascii', errors='replace').decode('ascii')
        post_safe = res_corrected.text.encode('ascii', errors='replace').decode('ascii')
        print(f"  Clip {item['id']} ({item['category']}): Latency={latency:.1f}ms", flush=True)
        print(f"    GT:   \"{gt}\"", flush=True)
        print(f"    Raw:  \"{raw_safe}\"", flush=True)
        print(f"    Post: \"{post_safe}\"", flush=True)

    # Compute WER
    wer_raw = jiwer.wer(ground_truths, raw_hypotheses)
    wer_lexicon = jiwer.wer(ground_truths, lexicon_hypotheses)

    latencies_arr = np.array(latencies)
    p50_latency = float(np.percentile(latencies_arr, 50))
    p90_latency = float(np.percentile(latencies_arr, 90))
    p95_latency = float(np.percentile(latencies_arr, 95))

    print(f"\n=== ASR Benchmark Results ===")
    print(f"WER without Lexicon: {wer_raw * 100:.2f}%")
    print(f"WER with Lexicon:    {wer_lexicon * 100:.2f}%")
    print(f"Relative WER Change: {((wer_lexicon - wer_raw) / max(wer_raw, 0.001)) * 100:+.1f}%")
    print(f"End-to-End Latency:  p50={p50_latency:.1f}ms | p90={p90_latency:.1f}ms | p95={p95_latency:.1f}ms")

    return {
        "model_size": config.asr.model_size,
        "device": config.asr.device,
        "compute_type": config.asr.compute_type,
        "wer_without_lexicon": round(wer_raw * 100, 2),
        "wer_with_lexicon": round(wer_lexicon * 100, 2),
        "latency_p50_ms": round(p50_latency, 1),
        "latency_p90_ms": round(p90_latency, 1),
        "latency_p95_ms": round(p95_latency, 1),
        "clip_count": len(metadata)
    }


async def main():
    config = load_config("tiny")  # benchmark on tiny for fastest baseline measurement
    rec_dir = Path(__file__).resolve().parent / "recordings"
    dataset_path = Path(__file__).resolve().parent / "intent_test_dataset.json"

    # 1. Run Intent Benchmarks
    intent_results = await evaluate_intent_dataset(dataset_path)

    # 2. Run ASR Benchmarks
    asr_results = evaluate_asr_clips(rec_dir, config)

    # Combined results
    full_results = {
        "hardware": {
            "os": "Windows 11",
            "cpu": "Intel/AMD Multi-core Host",
            "gpu": "NVIDIA GeForce RTX 5070 (12GB VRAM)"
        },
        "intent_metrics": intent_results,
        "asr_metrics": asr_results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    out_file = Path(__file__).resolve().parent / "results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)

    print(f"\nAll benchmark results exported to {out_file} successfully!")


if __name__ == "__main__":
    asyncio.run(main())
