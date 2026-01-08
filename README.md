# Aether-Sight

Aether-Sight is a decentralized MTG remote-play platform designed around a heavy-duty Host Engine
(compute server) and a Thin Client (UI + video). The system is optimized for high-end rigs while
remaining functional on potato hardware.

## Clone & Run

### 1) Backend (Host Engine)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Compile the full 61k-card brain (first run):

```bash
python compile_brain.py --limit 61000 --output brain.pkl
```

Start the Host Engine API:

```bash
python main.py --host 0.0.0.0 --port 8000
```

Headless compute-server mode (broadcasts UDP presence):

```bash
python main.py --headless --host 0.0.0.0 --port 8000
```

### 2) Frontend (Thin Client)

```bash
cd frontend
npm install
npm run dev
```

The Vite server proxies API calls to the Host Engine when you use `/api` in the client.

## Project Layout

```
/backend  -> Host Engine (FastAPI, ORB/HSV/FLANN matcher, brain compiler)
/frontend -> Thin Client (React UI and camera pipeline)
```
