# Contributing to Hearth

Welcome to Hearth! We are participating in Hacktoberfest and love community contributions.
Whether you're fixing a typo, adding a new language pack, or optimizing model inference, we welcome you.

---

## Quickstart (Under 5 Minutes)

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/your-username/hearth.git
cd hearth

# Setup Python virtualenv
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r services/core/requirements.txt

# Setup frontend
cd apps/web
npm install
cd ../..
```

### 3. Run Tests
```bash
python -m pytest tests/ -v
```

### 4. Start Development Servers
In Terminal 1 (Backend API & WebSocket server):
```bash
uvicorn services.core.api.main:app --reload --port 8000
```

In Terminal 2 (Frontend Vite server):
```bash
cd apps/web
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Areas You Can Help With
Check out [`docs/issues.md`](docs/issues.md) for 10 curated "good first issue" tasks, including:
1. Adding new regional language packs & kinship names.
2. Expanding medical explanations in Doctor Visit mode.
3. Adding UI accessibility themes (e-ink mode, high-contrast colors).
4. Running benchmarks on new hardware profiles.

---

## Coding Standards & Pull Requests
- Keep changes focused and well-tested.
- Run `python -m pytest tests/` before submitting.
- Commit using Conventional Commits (`feat: ...`, `fix: ...`, `docs: ...`).
- All runtime features must remain 100% offline with zero cloud telemetry.
