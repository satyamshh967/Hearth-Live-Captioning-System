# Hearth — Good First Issues (Hacktoberfest Ready)

Welcome! Every issue below is scoped so that a newcomer can set up, implement, test, and submit a high-quality Pull Request in **under 30 minutes**.

---

### Issue 1: Add Spanish (Latin America) Language Pack
- **Area**: Language Packs / Lexicon
- **Scope**: Create `configs/language_packs/es_latam/` with 40+ Spanish kinship terms (*Abuelito, Tía, Primo*), dishes (*Arepas, Tamales, Empanadas*), and common elderly medicines (*Losartán, Metformina*).
- **Skill**: JSON / YAML editing.

### Issue 2: E-Ink High-Contrast Black & White Theme
- **Area**: Frontend UI / Accessibility
- **Scope**: Add an ultra-high-contrast pure monochrome e-ink theme to `apps/web/src/components/SettingsModal.tsx` optimized for outdoor daylight or daylight tablet stands.
- **Skill**: React, Tailwind CSS.

### Issue 3: Benchmark Hearth on Raspberry Pi 5 / Mini-PC
- **Area**: Eval & Benchmarks
- **Scope**: Run `eval/run_eval.py` on a Raspberry Pi 5 or low-power mini-PC running `tiny` profile. Append measured p50/p95 latency to `docs/benchmarks.md`.
- **Skill**: Python, hardware benchmarking.

### Issue 4: Bluetooth Lapel Mic Latency Compensation
- **Area**: Audio Processing / Worklet
- **Scope**: Add a selectable Bluetooth latency buffer offset (100ms / 200ms / 300ms) in `apps/web/src/services/audio.ts` for users wearing wireless lavalier microphones.
- **Skill**: TypeScript, Web Audio API.

### Issue 5: Add Bengali / Bangla Language Pack
- **Area**: Language Packs / Lexicon
- **Scope**: Create `configs/language_packs/bn_bd/` with common Bengali kinship titles (*Dadu, Didun, Mashimoni, Kakababu*) and food items (*Machher Jhol, Mishti Doi, Luchi*).
- **Skill**: JSON editing.

### Issue 6: Sound Effects Customizer (Selectable Chime Frequencies)
- **Area**: Audio / Accessibility
- **Scope**: Allow users with high-frequency hearing loss to pick lower-frequency chime tones (e.g. 260Hz C4 instead of 523Hz C5) in `apps/web/src/services/chime.ts`.
- **Skill**: TypeScript, Web Audio API.

### Issue 7: Export Transcript to PDF with Large Font Print Style
- **Area**: Frontend / Export
- **Scope**: Add a "Print Large-Type PDF" button in `apps/web/src/components/SessionHistoryModal.tsx` using browser print CSS `@media print` with 24pt font for physical reading.
- **Skill**: React, CSS print styles.

### Issue 8: Add Medical Jargon Glossary Search in Doctor Visit Mode
- **Area**: Core Intelligence / Medical
- **Scope**: Expand `MEDICAL_SIMPLIFICATIONS` in `services/core/llm/rule_fallback.py` to cover 25 additional geriatric health terms (e.g., *osteoarthritis, cataract, statins, creatinine*).
- **Skill**: Python dictionary expansion.

### Issue 9: Custom Hotword Biasing List Import via CSV
- **Area**: Lexicon / Store
- **Scope**: Add a `/api/lexicon/import-csv` endpoint to `services/core/api/main.py` allowing caregivers to bulk-upload family name lists from CSV or contacts.
- **Skill**: FastAPI, Python.

### Issue 10: Docker Compose Profile for Raspberry Pi (ARM64)
- **Area**: Packaging / DevOps
- **Scope**: Test and add a dedicated `docker-compose.pi.yml` with ARM64 base images and memory limits (2GB RAM cap).
- **Skill**: Docker, YAML.
