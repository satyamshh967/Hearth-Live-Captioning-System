import os
import sys
import json
import subprocess
from pathlib import Path
import soundfile as sf
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CLIPS = [
    {
        "id": "clip_01",
        "ground_truth": "Dadaji, did you take your Metformin today with warm water?",
        "speaker": "Priya",
        "category": "medication_direct",
    },
    {
        "id": "clip_02",
        "ground_truth": "Priya is coming for dinner, shall we prepare dal makhani?",
        "speaker": "Rohan",
        "category": "dinner_plan",
    },
    {
        "id": "clip_03",
        "ground_truth": "Rohan, please pass the roti and fresh paneer to Dadaji.",
        "speaker": "Sunita",
        "category": "dining_table",
    },
    {
        "id": "clip_04",
        "ground_truth": "Doctor Verma told us to check blood pressure tomorrow morning.",
        "speaker": "Priya",
        "category": "doctor_update",
    },
    {
        "id": "clip_05",
        "ground_truth": "Sunita, is the evening tea ready or should we make it later?",
        "speaker": "Rohan",
        "category": "tea_time",
    },
    {
        "id": "clip_06",
        "ground_truth": "Dadaji went for a peaceful morning walk in the park with Aarav.",
        "speaker": "Sunita",
        "category": "third_person_narration",
    },
    {
        "id": "clip_07",
        "ground_truth": "Beta, please finish your bowl of khichdi quickly.",
        "speaker": "Priya",
        "category": "child_address",
    },
    {
        "id": "clip_08",
        "ground_truth": "Listen Dadaji, we are going to Apollo Clinic on Thursday morning.",
        "speaker": "Rohan",
        "category": "clinic_reminder",
    },
    {
        "id": "clip_09",
        "ground_truth": "Dadi was saying that the sweet kheer is very delicious tonight.",
        "speaker": "Aarav",
        "category": "third_person_family",
    },
    {
        "id": "clip_10",
        "ground_truth": "Are you feeling cold Dadaji? Should I turn down the air conditioner?",
        "speaker": "Priya",
        "category": "comfort_check",
    },
    {
        "id": "clip_11",
        "ground_truth": "Could you please pass the water jug across the table?",
        "speaker": "Rohan",
        "category": "table_request",
    },
    {
        "id": "clip_12",
        "ground_truth": "Telmisartan tablet is kept on the dining table near your spectacles.",
        "speaker": "Sunita",
        "category": "medicine_location",
    },
    {
        "id": "clip_13",
        "ground_truth": "Yes Dadaji, we can watch the evening cricket match together after dinner.",
        "speaker": "Rohan",
        "category": "direct_agree",
    },
    {
        "id": "clip_14",
        "ground_truth": "Rameshji, please drink some water before taking Atorvastatin.",
        "speaker": "Sunita",
        "category": "direct_medicine",
    },
    {
        "id": "clip_15",
        "ground_truth": "Please pass the dal makhani and hot rotis across the table.",
        "speaker": "Priya",
        "category": "noisy_dinner_mix",
        "add_noise": True,
    },
    {
        "id": "clip_16",
        "ground_truth": "Doctor noted age-related presbycusis and recommended continuing daily routine.",
        "speaker": "Priya",
        "category": "doctor_visit_summary",
    },
]


def add_dinner_noise(wav_path: Path):
    audio, sr = sf.read(str(wav_path))
    noise = np.random.normal(0, 0.04, len(audio))
    # Add ambient dining cutlery clinks
    clink_indices = np.random.choice(len(audio), size=8, replace=False)
    for idx in clink_indices:
        clink_len = min(400, len(audio) - idx)
        t = np.linspace(0, 0.03, clink_len)
        noise[idx:idx+clink_len] += 0.25 * np.sin(2 * np.pi * 2800 * t) * np.exp(-t * 80)
    
    mixed = audio + noise
    max_val = np.max(np.abs(mixed))
    if max_val > 0:
        mixed = mixed / max_val * 0.9
    sf.write(str(wav_path), mixed.astype(np.float32), sr)


def main():
    root_dir = Path(__file__).resolve().parent
    out_dir = root_dir / "recordings"
    out_dir.mkdir(parents=True, exist_ok=True)
    synth_script = root_dir / "synth.ps1"

    metadata = []
    print(f"Synthesizing {len(CLIPS)} acoustic speech clips using Windows Speech Synthesizer...")

    for item in CLIPS:
        wav_path = out_dir / f"{item['id']}.wav"
        
        # Invoke synth.ps1
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(synth_script),
            "-Text", item["ground_truth"],
            "-OutputFile", str(wav_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error synthesizing {item['id']}: {res.stderr}")
            continue

        if item.get("add_noise"):
            add_dinner_noise(wav_path)

        audio, sr = sf.read(str(wav_path))
        duration = len(audio) / sr

        metadata.append({
            "id": item["id"],
            "file": f"{item['id']}.wav",
            "ground_truth": item["ground_truth"],
            "speaker": item["speaker"],
            "category": item["category"],
            "duration_sec": round(duration, 2),
            "noisy": item.get("add_noise", False)
        })
        print(f"  [OK] Synthesized {item['id']}.wav ({duration:.2f}s) - \"{item['ground_truth'][:40]}...\"")

    meta_file = out_dir / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nAll {len(metadata)} clips synthesized successfully! Metadata saved to {meta_file}")


if __name__ == "__main__":
    main()
